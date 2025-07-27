from typing import Collection, cast

from django.apps import apps
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext as _
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.data_exchange.models import ExportTask, ImportTask
from core.data_exchange.permissions import (
    CanViewExportAndImportTask,
    MODEL_PERMISSIONS,
)
from core.data_exchange.serializers import (
    ExportTaskSerializer,
    ImportTaskSerializer,
)


def _get_allowed_model_names(request: Request) -> list[str]:
    AccountUser = apps.get_model("accounts", "AccountUser")
    user_permissions = cast(AccountUser, request.user).user_permissions.values(
        "codename"
    )
    models_names: list[str] = []
    for model_name, permission in MODEL_PERMISSIONS.items():
        if not isinstance(permission, Collection):
            permission = {permission}
        if permission.intersection(set(user_permissions)):
            models_names.append(model_name)
    return models_names


class ExportTaskViewSet(
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = ExportTaskSerializer
    permission_classes = [CanViewExportAndImportTask]

    def get_queryset(self) -> QuerySet[ExportTask]:
        from accounts.models import AccountUser, UserType

        base_queryset: QuerySet = ExportTask.objects.select_related("content_type")
        queryset = base_queryset.filter(owner_id=self.request.owner_id)
        if cast(AccountUser, self.request.user).user_type == UserType.STAFF:
            queryset = queryset.filter(
                content_type__model__in=_get_allowed_model_names(self.request)
            )
        return queryset

    @action(
        detail=True,
        methods=["GET"],
        url_path="file-serve",
        url_name="file_serve",
    )
    def serve_exported_file(self, request: Request, *args, **kwargs) -> HttpResponse:
        """
        Serves the exported file, if the file export is complete. Otherwise, return a json response with current
        task data.
        """
        task: ExportTask = self.get_object()
        if not task.external_file_id:
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        # TODO: Implement a factory that returns a processor for third-party storage platforms like AWS/Cloudinary
        #  based on the instance of the task to get the file url
        #  also see: core.data_exchange.includes.record_exporter.RecordExporter._save_to_external_service
        signed_url = ...  # TODO
        if not signed_url:
            raise NotFound(detail=_("File not found"))
        return HttpResponseRedirect(signed_url)

    @action(
        detail=True,
        methods=["POST"],
        url_path="notify-on-success",
        url_name="notify_on_success",
    )
    def notify_on_success(self, request: Request, *args, **kwargs) -> Response:
        task: ExportTask = self.get_object()
        task.notify_on_success = True
        task.save(update_fields=["notify_on_success", "last_modified_at"])
        return Response(self.get_serializer(task).data)


class ImportTaskViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = ImportTaskSerializer
    permission_classes = [CanViewExportAndImportTask]

    def get_queryset(self) -> QuerySet[ExportTask]:
        base_queryset: QuerySet = ImportTask.objects.select_related("content_type")
        queryset = base_queryset.filter(owner_id=self.request.owner_id)
        if cast(AccountUser, self.request.user).user_type == UserType.STAFF:
            queryset = queryset.filter(
                content_type__model__in=_get_allowed_model_names(self.request)
            )
        return queryset
