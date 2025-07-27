from typing import Any, cast, List, Union

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import AccountUser
from core.common.permissions import AccountsPermissions
from accounts.role_permissions import RoleBasedPermission


class IsOwnerOrReadOnly(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)
        return user.is_staff or request.method in SAFE_METHODS or user.is_owner

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)
        return user.is_staff or obj.owner == user


class CanManageAccountUsers(IsOwnerOrReadOnly):
    CAN_MANAGER_RESIDENTS = (
        f"accounts.{AccountsPermissions.ManageResidents}"  # for staff
    )

    CAN_MANAGE_USERS = (
        f"accounts.{AccountsPermissions.ManageAccountUser}"  # for members
    )

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)
        return (
            user.is_staff
            or request.method in SAFE_METHODS
            or user.is_owner
            or user.is_cluster_staff
            or user.has_any_permission(
                [self.CAN_MANAGE_USERS, self.CAN_MANAGER_RESIDENTS]
            )
        )

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        is_same_user = obj.id == user.id

        staff_can_modify_account = user.is_cluster_staff and user.has_perm(
            self.CAN_MANAGER_RESIDENTS
        )
        user_can_modify_account = user.get_owner() == obj.owner and user.has_perm(
            self.CAN_MANAGE_USERS
        )

        return (
            user.is_staff
            or is_same_user
            or staff_can_modify_account
            or user_can_modify_account
        )


class IsClusterAdmin(BasePermission):
    message = "Only cluster admins can perform this action!"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return cast(AccountUser, request.user).is_cluster_admin


class IsClusterStaffOrAdmin(BasePermission):
    """
    Permission class that allows access to cluster staff and admins.
    """
    message = "Only cluster staff or admins can perform this action!"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)
        return user.is_cluster_staff or user.is_cluster_admin


class HasClusterPermission(RoleBasedPermission):
    """
    Permission class that checks if the user has the specified permission for the current cluster.

    This class extends RoleBasedPermission to provide a cleaner, more maintainable
    implementation that eliminates string manipulation and code duplication.

    Usage:
        permission_classes = [HasClusterPermission(AccessControlPermissions.ManageVisitRequest)]
    """

    def __init__(
        self, permission: Union[str, List[str]], allow_safe_methods: bool = False
    ):
        """
        Initialize the permission class.

        Args:
            permission: Single permission or list of permissions to check
            allow_safe_methods: Whether to allow safe methods without specific permissions
        """
        super().__init__()

        # Convert single permission to list for consistency
        if isinstance(permission, str):
            self.required_permissions = [permission]
        else:
            self.required_permissions = permission

        self.allow_safe_methods = allow_safe_methods

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Enhanced object permission checking with better ownership detection.
        """
        user = cast(AccountUser, request.user)

        # Use parent class logic for basic permission checks
        if not super().has_object_permission(request, view, obj):
            return False

        # Additional ownership checks for specific object types
        if hasattr(obj, "owner") and obj.owner == user:
            return True

        if hasattr(obj, "invited_by") and str(obj.invited_by) == str(user.id):
            return True

        if hasattr(obj, "created_by") and str(obj.created_by) == str(user.id):
            return True

        # If we have required permissions, check them
        if self.required_permissions:
            return user.has_any_permission(self.required_permissions)

        return False


class HasSpecificPermission(RoleBasedPermission):
    """
    A more flexible permission class that can be configured for specific use cases.

    This class provides a cleaner alternative to HasClusterPermission with better
    configuration options and more explicit permission handling.
    """

    def __init__(
        self,
        permissions: Union[str, List[str]],
        allow_safe_methods: bool = False,
        allow_staff: bool = True,
        allow_cluster_admin: bool = True,
        check_ownership: bool = True,
    ):
        """
        Initialize the permission class.

        Args:
            permissions: Permission(s) to check
            allow_safe_methods: Whether to allow safe methods without permissions
            allow_staff: Whether staff can bypass permission checks
            allow_cluster_admin: Whether cluster admins can bypass permission checks
            check_ownership: Whether to check object ownership
        """
        super().__init__()

        if isinstance(permissions, str):
            self.required_permissions = [permissions]
        else:
            self.required_permissions = permissions

        self.allow_safe_methods = allow_safe_methods
        self.allow_staff = allow_staff
        self.allow_cluster_admin = allow_cluster_admin
        self.check_ownership = check_ownership

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Check object permissions with configurable ownership checking.
        """
        user = cast(AccountUser, request.user)

        # Use parent class logic for basic permission checks
        if not super().has_object_permission(request, view, obj):
            return False

        # Check ownership if enabled
        if self.check_ownership:
            if hasattr(obj, "owner") and obj.owner == user:
                return True

            if hasattr(obj, "user") and obj.user == user:
                return True

            if isinstance(obj, AccountUser) and obj == user:
                return True

        # Check specific permissions
        if self.required_permissions:
            return user.has_any_permission(self.required_permissions)

        return False
