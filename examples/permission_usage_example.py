"""
Example usage of the improved permission system in ClustR.

This file demonstrates how to use the new permission classes and utilities
for better maintainability and type safety.
"""

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import HasClusterPermission, HasSpecificPermission
from accounts.permission_utils import normalize_permissions, accounts_permissions
from core.common.permissions import (
    AccountsPermissions,
    AccessControlPermissions,
    SecurityPermissions,
)


class ExampleUserViewSet(ModelViewSet):
    """
    Example viewset showing different ways to use the improved permission system.
    """

    # Method 1: Using HasClusterPermission with permission constants
    permission_classes = [
        HasClusterPermission(
            permission=f"accounts.{AccountsPermissions.ManageAccountUser}",
            allow_safe_methods=True,
        )
    ]

    def get_permissions(self):
        """
        Method 2: Dynamic permission classes based on action.
        """
        if self.action == "list":
            # Allow safe methods for listing
            return [
                HasClusterPermission(
                    permission=f"accounts.{AccountsPermissions.ViewAccountUser}",
                    allow_safe_methods=True,
                )
            ]
        elif self.action == "create":
            # Require specific permission for creation
            return [
                HasClusterPermission(
                    permission=f"accounts.{AccountsPermissions.ManageAccountUser}"
                )
            ]
        elif self.action == "update":
            # Use the more flexible HasSpecificPermission
            return [
                HasSpecificPermission(
                    permissions=[
                        f"accounts.{AccountsPermissions.ManageAccountUser}",
                        f"accounts.{AccountsPermissions.ManageResidents}",
                    ],
                    allow_safe_methods=False,
                    check_ownership=True,
                )
            ]

        # Default to the class-level permissions
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """
        Method 3: Using permission utilities for cleaner code.
        """
        # Use the permission builder for type-safe permission strings
        required_permissions = accounts_permissions.permissions(
            "ManageAccountUser", "ManageResidents"
        )

        # Or use the normalize_permissions utility
        permissions = normalize_permissions(
            [
                AccountsPermissions.ManageAccountUser,
                "accounts.manageresidents",  # Mixed format
            ]
        )

        # Both approaches work the same way
        permission_class = HasSpecificPermission(
            permissions=required_permissions, check_ownership=True
        )

        # Check permission manually if needed
        if not permission_class.has_permission(request, self):
            return Response({"error": "Permission denied"}, status=403)

        # Your view logic here
        return Response({"status": "activated"})


class ExampleSecurityViewSet(ModelViewSet):
    """
    Example showing how to use permissions for security-related features.
    """

    def get_permissions(self):
        """
        Method 4: Using multiple permission types with different configurations.
        """
        if self.action in ["list", "retrieve"]:
            # View permissions with safe methods allowed
            return [
                HasSpecificPermission(
                    permissions=[
                        f"security.{SecurityPermissions.ViewSecurityLog}",
                        f"security.{SecurityPermissions.ViewSecurityAlert}",
                    ],
                    allow_safe_methods=True,
                    allow_staff=True,
                    allow_cluster_admin=True,
                )
            ]

        elif self.action in ["create", "update", "partial_update", "destroy"]:
            # Manage permissions - more restrictive
            return [
                HasSpecificPermission(
                    permissions=[
                        f"security.{SecurityPermissions.ManageSecurityLog}",
                        f"security.{SecurityPermissions.ManageSecurityAlert}",
                    ],
                    allow_safe_methods=False,
                    allow_staff=True,
                    allow_cluster_admin=True,
                    check_ownership=False,  # Security logs might not have owners
                )
            ]

        return super().get_permissions()


class ExampleAccessControlViewSet(ModelViewSet):
    """
    Example showing how to use permissions for access control features.
    """

    # Method 5: Using permission constants directly
    permission_classes = [
        HasClusterPermission(
            permission=f"accesscontrol.{AccessControlPermissions.ManageVisitRequest}",
            allow_safe_methods=True,
        )
    ]

    @action(detail=False, methods=["post"])
    def bulk_approve(self, request):
        """
        Method 6: Custom permission checking for complex operations.
        """
        # For complex operations, you might want to check multiple permissions
        required_permissions = [
            f"accesscontrol.{AccessControlPermissions.ManageVisitRequest}",
            f"accesscontrol.{AccessControlPermissions.ManageGuest}",
        ]

        # Use the utility to normalize and validate
        normalized_permissions = normalize_permissions(required_permissions)

        # Create a temporary permission class for this specific action
        temp_permission = HasSpecificPermission(
            permissions=normalized_permissions,
            allow_safe_methods=False,
            check_ownership=False,  # Bulk operations might not be owner-specific
        )

        if not temp_permission.has_permission(request, self):
            return Response({"error": "Insufficient permissions"}, status=403)

        # Your bulk approval logic here
        return Response({"status": "bulk_approved"})


# Example of how to use the permission utilities in other parts of your code
def example_permission_utility_usage():
    """
    Examples of using the permission utilities in other parts of your application.
    """

    # Building permission strings
    from accounts.permission_utils import build_permission_string

    permission_string = build_permission_string(
        AccountsPermissions, "ManageAccountUser"
    )
    # Result: "accounts.manageaccountuser"

    # Getting all permissions from a class
    from accounts.permission_utils import get_permissions_from_class

    all_account_permissions = get_permissions_from_class(AccountsPermissions)
    # Result: ["accounts.viewaccountuser", "accounts.manageaccountuser", ...]

    # Validating permission strings
    from accounts.permission_utils import validate_permission_string

    is_valid = validate_permission_string("accounts.manageaccountuser")
    # Result: True

    # Using the permission builder
    from accounts.permission_utils import accounts_permissions

    user_permissions = accounts_permissions.permissions(
        "ManageAccountUser", "ViewResidents", "ManageRoles"
    )
    # Result: ["accounts.manageaccountuser", "accounts.viewresidents", "accounts.manageroles"]

    return {
        "permission_string": permission_string,
        "all_permissions": all_account_permissions,
        "is_valid": is_valid,
        "user_permissions": user_permissions,
    }
