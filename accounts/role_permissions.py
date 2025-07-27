"""
Enhanced role-based permissions for ClustR application.
"""

from typing import Any, List, cast

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import AccountUser, Role
from core.common.permissions import (
    AccountsPermissions,
    AdminPermissions,
    CommunicationsPermissions,
    ProfilePermissions,
    SecurityPermissions,
)


class RoleBasedPermission(BasePermission):
    """
    Base class for role-based permissions.

    This class provides common functionality for checking permissions
    based on user roles and specific permissions.
    """

    # Required permissions for this permission class
    required_permissions: List[str] = []

    # Whether to allow staff users to bypass permission checks
    allow_staff: bool = True

    # Whether to allow cluster admins to bypass permission checks
    allow_cluster_admin: bool = True

    # Whether to allow safe methods (GET, HEAD, OPTIONS) without specific permissions
    allow_safe_methods: bool = False

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Check if the user has permission to access the view.

        Args:
            request: The request object
            view: The view being accessed

        Returns:
            True if the user has permission, False otherwise
        """
        user = cast(AccountUser, request.user)

        # Anonymous users never have permission
        if not user.is_authenticated:
            return False

        # Staff users can bypass permission checks if allowed
        if self.allow_staff and user.is_staff:
            return True

        # Cluster admins can bypass permission checks if allowed
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True

        # Allow safe methods if configured
        if self.allow_safe_methods and request.method in SAFE_METHODS:
            return True

        # Check if user has any of the required permissions
        if self.required_permissions and user.has_any_permission(
            self.required_permissions
        ):
            return True

        # Default to no permission
        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Check if the user has permission to access the object.

        Args:
            request: The request object
            view: The view being accessed
            obj: The object being accessed

        Returns:
            True if the user has permission, False otherwise
        """
        user = cast(AccountUser, request.user)

        # Anonymous users never have permission
        if not user.is_authenticated:
            return False

        # Staff users can bypass permission checks if allowed
        if self.allow_staff and user.is_staff:
            return True

        # Cluster admins can bypass permission checks if allowed
        if self.allow_cluster_admin and user.is_cluster_admin:
            return True

        # Allow safe methods if configured
        if self.allow_safe_methods and request.method in SAFE_METHODS:
            return True

        # Check if user has any of the required permissions
        if self.required_permissions and user.has_any_permission(
            self.required_permissions
        ):
            # For objects with an owner field, check if the user is the owner
            if hasattr(obj, "owner"):
                return obj.owner == user or obj.owner == user.get_owner()

            # For objects with a user field, check if the user is the user
            if hasattr(obj, "user"):
                return obj.user == user

            # For AccountUser objects, check if the user is the object or its owner
            if isinstance(obj, AccountUser):
                return obj == user or obj.owner == user or obj == user.get_owner()

        # Default to no permission
        return False


class IsOwnerOrAdmin(RoleBasedPermission):
    """
    Permission class that allows access to owners and admins.
    """

    allow_safe_methods = True

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)
        return user.is_authenticated and (
            user.is_staff
            or user.is_cluster_admin
            or user.is_owner
            or request.method in SAFE_METHODS
        )

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # For objects with an owner field, check if the user is the owner
        if hasattr(obj, "owner"):
            return obj.owner == user or obj.owner == user.get_owner()

        # For objects with a user field, check if the user is the user
        if hasattr(obj, "user"):
            return obj.user == user

        # For AccountUser objects, check if the user is the object or its owner
        if isinstance(obj, AccountUser):
            return obj == user or obj.owner == user or obj == user.get_owner()

        # Default to no permission
        return False


class CanManageUsers(RoleBasedPermission):
    """
    Permission class for managing users.
    """

    required_permissions = [
        f"accounts.{AccountsPermissions.ManageAccountUser}",
        f"accounts.{AccountsPermissions.ManageResidents}",
    ]

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # Users can always manage themselves
        if isinstance(obj, AccountUser) and obj.id == user.id:
            return True

        # Check if user has permission to manage users
        if user.has_perm(f"accounts.{AccountsPermissions.ManageAccountUser}"):
            # For AccountUser objects, check if the user is the owner
            if isinstance(obj, AccountUser):
                return obj.owner == user or obj.get_owner() == user

        # Check if user has permission to manage residents
        if user.is_cluster_staff and user.has_perm(
            f"accounts.{AccountsPermissions.ManageResidents}"
        ):
            # For AccountUser objects, check if they're in the same cluster
            if isinstance(obj, AccountUser):
                # Check if they share any clusters
                user_clusters = set(user.clusters.values_list("id", flat=True))
                obj_clusters = set(obj.clusters.values_list("id", flat=True))
                return bool(user_clusters.intersection(obj_clusters))

        # Default to no permission
        return False


class CanManageRoles(RoleBasedPermission):
    """
    Permission class for managing roles.
    """

    required_permissions = [f"accounts.{AccountsPermissions.ManageRoles}"]

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # Check if user has permission to manage roles
        if user.has_perm(f"accounts.{AccountsPermissions.ManageRoles}"):
            # For Role objects, check if the user is the owner
            if isinstance(obj, Role):
                return obj.owner == user or obj.owner == user.get_owner()

        # Default to no permission
        return False


class CanViewAdminSettings(RoleBasedPermission):
    """
    Permission class for viewing admin settings.
    """

    required_permissions = [
        f"admin.{AdminPermissions.ViewClusterSettings}",
        f"admin.{AdminPermissions.ViewSystemSettings}",
    ]

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)

        # Only allow safe methods
        if request.method not in SAFE_METHODS:
            return False

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # Check if user has any of the required permissions
        return user.has_any_permission(self.required_permissions)


class CanManageAdminSettings(RoleBasedPermission):
    """
    Permission class for managing admin settings.
    """

    required_permissions = [
        f"admin.{AdminPermissions.ManageClusterSettings}",
        f"admin.{AdminPermissions.ManageSystemSettings}",
    ]


class CanViewSecuritySettings(RoleBasedPermission):
    """
    Permission class for viewing security settings.
    """

    required_permissions = [
        f"security.{SecurityPermissions.ViewSecurityLog}",
        f"security.{SecurityPermissions.ViewSecurityAlert}",
        f"security.{SecurityPermissions.ViewEmergencyResponse}",
    ]

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = cast(AccountUser, request.user)

        # Only allow safe methods
        if request.method not in SAFE_METHODS:
            return False

        # Staff, cluster admins, and security staff have permission
        if user.is_staff or user.is_cluster_admin or user.is_cluster_staff:
            return True

        # Check if user has any of the required permissions
        return user.has_any_permission(self.required_permissions)


class CanManageSecuritySettings(RoleBasedPermission):
    """
    Permission class for managing security settings.
    """

    required_permissions = [
        f"security.{SecurityPermissions.ManageSecurityLog}",
        f"security.{SecurityPermissions.ManageSecurityAlert}",
        f"security.{SecurityPermissions.ManageEmergencyResponse}",
    ]


class CanManageProfile(RoleBasedPermission):
    """
    Permission class for managing user profiles.
    """

    required_permissions = [
        f"profile.{ProfilePermissions.ManageProfile}",
        f"profile.{ProfilePermissions.ManageSettings}",
    ]

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # Users can always manage their own profile
        if isinstance(obj, AccountUser) and obj.id == user.id:
            return True

        # Check if user has permission to manage profiles
        if user.has_any_permission(self.required_permissions):
            # For AccountUser objects, check if the user is the owner
            if isinstance(obj, AccountUser):
                return obj.owner == user or obj.get_owner() == user

        # Default to no permission
        return False


class CanManageEmergencyContacts(RoleBasedPermission):
    """
    Permission class for managing emergency contacts.
    """

    required_permissions = [
        f"communications.{CommunicationsPermissions.ManageEmergencyContacts}",
    ]

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = cast(AccountUser, request.user)

        # Staff and cluster admins always have permission
        if user.is_staff or user.is_cluster_admin:
            return True

        # Check if the object has a user field
        if hasattr(obj, "user"):
            # Users can always manage their own emergency contacts
            if obj.user.id == user.id:
                return True

            # Check if user has permission to manage emergency contacts
            if user.has_any_permission(self.required_permissions):
                # Check if the user is the owner of the emergency contact's user
                return obj.user.owner == user or obj.user.get_owner() == user

        # Default to no permission
        return False
