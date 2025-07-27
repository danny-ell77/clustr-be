import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any, Type, cast

from django.apps import apps
from django.http.response import FileResponse, HttpResponseBase
from drf_yasg import openapi
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.common.exceptions import UnprocessedEntityException
from core.data_exchange import tasks
from core.data_exchange.exceptions import DataImportException
from core.data_exchange.includes.record_importer import RecordImporter
from core.data_exchange.includes.types import FileFormats
from core.data_exchange.models import ImportTask
from core.data_exchange.serializers import (
    BaseImportedDataSerializer,
    DataExchangeFileFormatSerializer,
    DynamicFieldsSerializer,
    ImportTaskSerializer,
)

export_template_file_format = openapi.Parameter(
    "file_format",
    openapi.IN_QUERY,
    description="Preferred File format - XLSX or CSV. Defaults to XLSX",
    type=openapi.TYPE_INTEGER,
    required=False,
    enum=[member.value for member in DataExchangeFileFormatSerializer.allowed_formats],
)


class GenericModelImporter:
    """
    Provides a high level abstraction over the core RecordImport class and adds functionality for asynchronous
    and synchronous data import. Also, helps to streamline the client code in the views.
    """

    def __init__(
        self,
        request: Request,
        import_serializer_class: Type[DynamicFieldsSerializer],
        import_data_serializer_class: Type[BaseImportedDataSerializer],
        is_async: bool,
        serializer_context: dict = None,
    ):
        """
        Parameters
        :param request: A Request object
        :param import_serializer_class: A serializer class that will process the imported file data. Its save method
          should return ResultOutput containing the imported data
        :param import_data_serializer_class: A serializer class that will be used to validate the client's request
          data
        :param is_async: Flag to determine if the import should be done synchronously or asynchronously
        :param serializer_context: Optional context data that will be passed to the serializers
        """
        self.request = request
        self.import_serializer_class = import_serializer_class
        self._import_data_serializer_class = import_data_serializer_class
        self.serializer_context = serializer_context or {} | {
            "cluster_id": self.request.user.cluster_id,
            "owner_id": self.request.user.get_owner().id,
            "cluster_staff_id": self.request.user.id,
        }
        self.is_async = is_async
        self._import_data: dict[str, Any] = {}

    def get_response(self) -> HttpResponseBase:
        serializer = self._import_data_serializer_class(
            data=self.request.data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        self._import_data = serializer.validated_data
        return self._get_import_response()

    def _get_import_response(self) -> HttpResponseBase:
        if self.is_async:
            return self._import_asynchronously()

        # Going synchronous...
        try:
            importer = RecordImporter(
                import_data=self._import_data,
                import_serializer_class=self.import_serializer_class,
                serializer_context=self.serializer_context,
            )
            result = importer.import_()
            if result.data:
                return Response(result.data, status=status.HTTP_200_OK)
            if result.errors:
                return Response(
                    result.serialized_errors(), status=status.HTTP_400_BAD_REQUEST
                )
            return Response(result.data, status=status.HTTP_200_OK)

        except DataImportException as error:
            raise UnprocessedEntityException(detail=str(error))

    def _import_asynchronously(self) -> Response:
        task = self._create_import_task()
        tasks.import_records.apply_async(
            kwargs={
                "import_data": self._import_data,
                "import_serializer_class": self.import_serializer_class,
                "serializer_context": self.serializer_context,
                "task": task,
            },
            serializer="pickle",
            ignore_result=self.is_async,
        )
        return Response(
            ImportTaskSerializer(task).data, status=status.HTTP_202_ACCEPTED
        )

    def _create_import_task(self) -> ImportTask:
        AccountUser = apps.get_model("users", "AccountUser")
        return ImportTask.create_in_progress_task(
            content_type=self.import_serializer_class.get_content_type(),
            owner_id=self.request.user.get_owner().id,
            created_by=cast(AccountUser, self.request.user),
            notify_on_success=False,
        )

    @classmethod
    def serve_template_file(
        cls, request: Request, template_path_prefix: Path, name: str
    ) -> FileResponse:
        """
        Returns a CSV or Excel template file to serve as a starter/guide to users on the format for import
        """
        value = request.query_params.get("file_format", "")
        file_format = FileFormats.XLSX
        if value.isdigit():
            value = int(value)
            serializer = DataExchangeFileFormatSerializer(data={"format": value})
            serializer.is_valid(raise_exception=True)
            file_format = FileFormats(serializer.validated_data["format"])

        suffix = ".xlsx" if file_format == FileFormats.XLSX else ".csv"
        template_path = template_path_prefix / f"{name}{suffix}"

        with template_path.open(mode="rb") as file:
            mimetype = mimetypes.guess_type(template_path)[0]
            response = FileResponse(
                streaming_content=BytesIO(file.read()),
                as_attachment=True,
                filename=f"{name}{suffix}",
            )
            response["Content-Type"] = mimetype
            return response
