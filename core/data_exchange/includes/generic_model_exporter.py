from datetime import timedelta
from io import BytesIO
from typing import Optional, Type
from uuid import UUID

from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.result import AsyncResult
from django.db.models import QuerySet
from django.http.response import HttpResponseBase, FileResponse
from django.utils.functional import cached_property
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.data_exchange import tasks
from core.data_exchange.includes.types import (
    FileFormats,
    ExportOutput,
    StorageLocations,
)
from core.data_exchange.includes.utils import decode_output_result
from core.data_exchange.models import ExportTask
from core.data_exchange.serializers import (
    ExportTaskSerializer,
    DynamicFieldsSerializer,
    BaseExportOptionsSerializer,
)

# The maximum number of record size that can be exported in a synchronous request
MAX_SYNC_RECORD_SIZE = 1000

# Block for at most 60 seconds in synchronous exports
REQUEST_BLOCK_TIMEOUT = timedelta(minutes=1).total_seconds()


class GenericModelExporter:
    """
    Exports list-serializable data as XLSX or CSV file. The export will be executed synchronously if the number
    of records to export is below the threshold - MAX_SYNC_RECORD_SIZE. That means the request will be blocked.
    However, if the blocking time exceeds the threshold - REQUEST_BLOCK_TIMEOUT, a response is returned with a
    task id that the client can use to check the status of the export or download the result when it is ready.
    Export task itself supports notification when results are available, so an email notification will be sent
    to the client when the results are ready for download. See class: core.data_exchange.models.ExportTask

    **Note, this class does not validate the ownership or access permission of the request user and the data to export.
    The clients of the class is responsible for passing in appropriate queryset that has been checked for access
    permission and user authorization.
    """

    def __init__(
        self,
        request: Request,
        base_queryset: QuerySet,
        export_serializer_class: Type[DynamicFieldsSerializer],
        options_serializer_class: Type[BaseExportOptionsSerializer],
        pk_filter_look_up="pk__in",
        force_async=False,
    ):
        """
        Parameters
        :param request: A HTTPRequest/Request instance
        :param base_queryset: The queryset to export. All data in the queryset will be exported. To provide extra
          filtering, user the ids filter in the argument - options_serializer_class
        :param export_serializer_class: A Serializer subclass that will receive the queryset for serialization as
          a list (with parameter many=True). The serializer is responsible for transforming the queryset to a list
          of data that will then be written to the output CSV or XLSX file
        :param options_serializer_class: A subclass of
          core.data_exchange.serializers.BaseExportOptionsSerializer that captures the client's
          export preferences such as the file format, exact object ids to export and the fields to export
        :param pk_filter_look_up: Django's look_up expression to use to further filter the queryset
        :param force_async: Force the export to be performed asynchronously without any blocking
        """
        self.request = request
        self.base_queryset = base_queryset
        self.export_serializer_class = export_serializer_class
        self.options_serializer_class = options_serializer_class
        self.pk_filter_look_up = pk_filter_look_up
        self.force_async = force_async
        self._data: Optional[dict] = None
        self._export_queryset: Optional[QuerySet] = None
        self._task: Optional[ExportTask] = None

    @property
    def _owner_id(self) -> UUID:
        return self.request.user.owner_id

    def get_response(self) -> HttpResponseBase:
        serializer = self.options_serializer_class(
            data=self.request.data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        self._data = serializer.data
        self._export_queryset = self._get_export_queryset(ids=self._data["ids"])
        self._task = self._create_export_task(
            self._export_queryset, self._data["notify_on_success"]
        )
        async_result = self._schedule_export_task()
        return self._get_export_response(async_result)

    def _get_export_queryset(self, ids: Optional[list]):
        if self.pk_filter_look_up is None or not ids:
            return self.base_queryset
        return self.base_queryset.filter(**{self.pk_filter_look_up: ids})

    def _create_export_task(
        self, queryset: QuerySet, notify_on_success: bool
    ) -> ExportTask:
        task = ExportTask.create_in_progress_task(
            owner_id=self._owner_id,
            created_by=self.request.user.id,
            queryset=queryset,
            notify_on_success=notify_on_success,
        )
        return task

    @cached_property
    def _is_async(self) -> bool:
        """Checks if an export task should be performed asynchronously"""
        if self.force_async:
            return True
        if self._task and self._task.notify_on_success:
            return True
        count = self._export_queryset.count()
        return not count <= MAX_SYNC_RECORD_SIZE

    def _schedule_export_task(self):
        async_result = tasks.export_records.apply_async(
            kwargs={
                "model_class": self.base_queryset.model,
                "queryset_dict": self._export_queryset.__dict__,
                "serializer_class": self.export_serializer_class,
                "serializer_extra_fields": self._data["extra_fields"],
                "task": self._task,
                "output_format": FileFormats(self._data["format"]),
                "storage_location": StorageLocations.MEMORY_FILE,
                "owner_id": self._owner_id,
            },
            serializer="pickle",
            ignore_result=self._is_async,
        )
        return async_result

    def _get_export_response(self, async_result: AsyncResult) -> HttpResponseBase:
        """
        For async exports, wait to get results. If the result takes more than 10 seconds (REQUEST_BLOCK_TIMEOUT)
        to generate, return task object with id to check the status and retrieve results later.
        """
        if self._is_async:
            return Response(
                ExportTaskSerializer(self._task).data, status=status.HTTP_202_ACCEPTED
            )
        while not async_result.ready():
            try:
                # Blocks the thread until result is ready or timeout is reached.
                async_result.wait(timeout=REQUEST_BLOCK_TIMEOUT)
                result = ExportOutput(*async_result.get())
                file = decode_output_result(result.file)
                response = FileResponse(
                    streaming_content=BytesIO(file),
                    as_attachment=True,
                    filename=result.file_name,
                )
                response["Content-Type"] = result.mime_type
                return response
            except CeleryTimeoutError:
                # Going asynchronous... The client can check the task status and get results later using the export
                # task id. An email may also be sent when the data is ready.
                return Response(
                    ExportTaskSerializer(self._task).data,
                    status=status.HTTP_202_ACCEPTED,
                )
