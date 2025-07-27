from typing import cast, TYPE_CHECKING, Union

from django.db.models import TextChoices
from django.views import View
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from core.common.permissions import AccountsPermissions
from core.data_exchange.models import ExportTask

if TYPE_CHECKING:
    from accounts.models import AccountUser

MODEL_PERMISSIONS: dict[str, Union[TextChoices, set[TextChoices]]] = {
    "accountuser": {
        AccountsPermissions.ManageAccountUser,
        AccountsPermissions.ManageResidents,
    }
}


class CanViewExportAndImportTask(BasePermission):
    def has_object_permission(
        self, request: Request, view: View, obj: ExportTask
    ) -> bool:
        user = cast(AccountUser, request.user)
        if not user.is_cluster_staff:
            return False
        if user.is_cluster_admin:
            return True
        model_name = cast(str, obj.content_type.model).lower()
        required_permission = MODEL_PERMISSIONS.get(model_name)
        if not required_permission:
            return False
        user_permissions = user.roles.permissions.values_list("codename", flat=True)
        object_user_permissions = set(user_permissions).intersection(
            required_permission
        )
        return bool(object_user_permissions)
