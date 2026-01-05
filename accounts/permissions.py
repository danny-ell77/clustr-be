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
    """
    Permission class for managing account users.

    Attributes:
        CAN_MANAGER_RESIDENTS: Permission required for staff to manage residents
        CAN_MANAGE_USERS: Permission required for members to manage users
    """

    CAN_MANAGER_RESIDENTS = f"accounts.{AccountsPermissions.ManageResidents}"
    CAN_MANAGE_USERS = f"accounts.{AccountsPermissions.ManageAccountUser}"

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


class HasClusterPermission(BasePermission):
    """
    Permission class that checks if the user has the specified permission for the current cluster.
    Uses a factory pattern to avoid instantiation issues with DRF.

    Usage:
        permission_classes = [
            HasClusterPermission.check_permissions(
                for_view=[AccessControlPermissions.ManageVisitRequest]
            )
        ]
    """

    view_permissions: List[str] = []
    obj_permissions: List[str] = []
    allow_staff: bool = True
    allow_cluster_admin: bool = True
    check_ownership: bool = True

    @classmethod
    def check_permissions(
        cls,
        for_view: Union[str, List[str]] = None,
        for_object: Union[str, List[str]] = None,
        allow_staff: bool = True,
        allow_cluster_admin: bool = True,
        check_ownership: bool = True,
    ):
        """
        Returns a subclass that enforces view and object permissions.
        
        Args:
            for_view: Permission(s) to check for the view
            for_object: Permission(s) to check for the object
            allow_staff: Whether staff can bypass permission checks
            allow_cluster_admin: Whether cluster admins can bypass permission checks
            check_ownership: Whether to check object ownership
        
        Usage:
            permission_classes = [
                HasClusterPermission.check_permissions(
                    for_view=[AccessControlPermissions.ManageVisitRequest],
                    for_object=[AccessControlPermissions.ManageVisitRequest]
                )
            ]
        """
        view_perms = [for_view] if isinstance(for_view, str) else (for_view or [])
        obj_perms = [for_object] if isinstance(for_object, str) else (for_object or [])
        
        # Normalize permissions by adding app label if missing
        view_perms = [perm if "." in perm else f"accounts.{perm}" for perm in view_perms]
        obj_perms = [perm if "." in perm else f"accounts.{perm}" for perm in obj_perms]
        
        return type(
            "HasClusterPermission",
            (cls,),
            {
                "view_permissions": view_perms,
                "obj_permissions": obj_perms,
                "allow_staff": allow_staff,
                "allow_cluster_admin": allow_cluster_admin,
                "check_ownership": check_ownership,
            },
        )

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check view-level permissions."""
        user = cast(AccountUser, request.user)
        
        if self.allow_staff and user.is_staff:
            return True
        
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True
        
        if not self.view_permissions:
            return True
        
        return user.has_any_permission(self.view_permissions)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """Check object-level permissions with ownership detection."""
        user = cast(AccountUser, request.user)
        
        if self.allow_staff and user.is_staff:
            return True
        
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True
        
        if self.check_ownership:
            if hasattr(obj, "owner") and obj.owner == user:
                return True
            if hasattr(obj, "invited_by") and str(obj.invited_by) == str(user.id):
                return True
            if hasattr(obj, "created_by") and str(obj.created_by) == str(user.id):
                return True
        
        if not self.obj_permissions:
            return True
        
        return user.has_any_permission(self.obj_permissions)


class HasSpecificPermission(BasePermission):
    """
    Simple permission checker that can be configured for view and object permissions.
    Uses a factory pattern to avoid instantiation issues with DRF.
    """
    
    view_permissions: List[str] = []
    obj_permissions: List[str] = []
    allow_staff: bool = True
    allow_cluster_admin: bool = True

    @classmethod
    def check_permissions(
        cls,
        for_view: Union[str, List[str]] = None,
        for_object: Union[str, List[str]] = None,
        allow_staff: bool = True,
        allow_cluster_admin: bool = True,
    ):
        """
        Returns a subclass that enforces view and object permissions.
        
        Args:
            for_view: Permission(s) to check for the view
            for_object: Permission(s) to check for the object
            allow_staff: Whether staff can bypass permission checks
            allow_cluster_admin: Whether cluster admins can bypass permission checks
        
        Usage:
            permission_classes = [
                HasSpecificPermission.check_permissions(
                    for_view=[PaymentsPermissions.ManageWallet],
                    for_object=[PaymentsPermissions.ManageWallet]
                )
            ]
        """
        view_perms = [for_view] if isinstance(for_view, str) else (for_view or [])
        obj_perms = [for_object] if isinstance(for_object, str) else (for_object or [])
        
        return type(
            "HasSpecificPermission",
            (cls,),
            {
                "view_permissions": view_perms,
                "obj_permissions": obj_perms,
                "allow_staff": allow_staff,
                "allow_cluster_admin": allow_cluster_admin,
            },
        )

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check view-level permissions."""
        user = cast(AccountUser, request.user)
        
        if self.allow_staff and user.is_staff:
            return True
        
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True
        
        if not self.view_permissions:
            return True
        
        return user.has_any_permission(self.view_permissions)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """Check object-level permissions."""
        user = cast(AccountUser, request.user)
        
        if self.allow_staff and user.is_staff:
            return True
        
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True
        
        if not self.obj_permissions:
            return True
        
        return user.has_any_permission(self.obj_permissions)
