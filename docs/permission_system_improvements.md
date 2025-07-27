# Permission System Improvements

## Overview

The ClustR permission system has been significantly improved to provide better maintainability, type safety, and consistency. This document outlines the changes and how to use the new system.

## Problems with the Original Implementation

### 1. String Manipulation Issues
The original `HasClusterPermission` class had several problems:

```python
# OLD - Fragile string manipulation
permission_class_name = self.permission.__class__.__name__
if permission_class_name.endswith('Permissions'):
    permission_class_name = permission_class_name[:-11]  # Remove 'Permissions' suffix
permission_string = f"{permission_class_name.lower()}.{self.permission}"
```

**Problems:**
- Manual string manipulation is error-prone
- Hard to maintain when permission class names change
- No validation of permission strings
- Inconsistent naming conventions

### 2. Code Duplication
Similar logic was repeated across multiple permission classes:
- Staff/admin bypass checks
- Ownership validation
- Permission string construction

### 3. Inconsistent Patterns
Different permission classes used different approaches:
- Some used string constants
- Others used direct permission objects
- Mixed validation strategies

## New Implementation

### 1. Improved `HasClusterPermission` Class

The new implementation extends `RoleBasedPermission` and eliminates string manipulation:

```python
class HasClusterPermission(RoleBasedPermission):
    """
    Permission class that checks if the user has the specified permission for the current cluster.
    
    Usage:
        permission_classes = [HasClusterPermission(AccessControlPermissions.ManageVisitRequest)]
    """
    
    def __init__(self, permission: Union[str, List[str]], allow_safe_methods: bool = False):
        super().__init__()
        
        # Convert single permission to list for consistency
        if isinstance(permission, str):
            self.required_permissions = [permission]
        else:
            self.required_permissions = permission
            
        self.allow_safe_methods = allow_safe_methods
```

**Benefits:**
- No string manipulation
- Consistent with existing `RoleBasedPermission` base class
- Type hints for better IDE support
- Flexible - accepts single permission or list

### 2. New `HasSpecificPermission` Class

A more flexible alternative with better configuration options:

```python
class HasSpecificPermission(RoleBasedPermission):
    def __init__(
        self, 
        permissions: Union[str, List[str]], 
        allow_safe_methods: bool = False,
        allow_staff: bool = True,
        allow_cluster_admin: bool = True,
        check_ownership: bool = True
    ):
```

**Features:**
- Configurable staff/admin bypass
- Optional ownership checking
- Support for multiple permissions
- Better control over safe method handling

### 3. Permission Utilities (`accounts/permission_utils.py`)

New utility functions for cleaner permission handling:

#### `build_permission_string()`
```python
from accounts.permission_utils import build_permission_string
from core.common.permissions import AccountsPermissions

permission_string = build_permission_string(AccountsPermissions, "ManageAccountUser")
# Result: "accounts.manageaccountuser"
```

#### `normalize_permissions()`
```python
from accounts.permission_utils import normalize_permissions

permissions = normalize_permissions([
    AccountsPermissions.ManageAccountUser,
    "accounts.viewresidents"  # Mixed format
])
# Result: ["accounts.manageaccountuser", "accounts.viewresidents"]
```

#### `PermissionBuilder` Class
```python
from accounts.permission_utils import accounts_permissions

user_permissions = accounts_permissions.permissions(
    "ManageAccountUser",
    "ViewResidents"
)
# Result: ["accounts.manageaccountuser", "accounts.viewresidents"]
```

## Usage Examples

### Basic Usage

```python
from accounts.permissions import HasClusterPermission
from core.common.permissions import AccountsPermissions

class UserViewSet(ModelViewSet):
    permission_classes = [
        HasClusterPermission(
            permission=f"accounts.{AccountsPermissions.ManageAccountUser}",
            allow_safe_methods=True
        )
    ]
```

### Dynamic Permissions

```python
def get_permissions(self):
    if self.action == 'list':
        return [HasClusterPermission(
            permission=f"accounts.{AccountsPermissions.ViewAccountUser}",
            allow_safe_methods=True
        )]
    elif self.action == 'create':
        return [HasClusterPermission(
            permission=f"accounts.{AccountsPermissions.ManageAccountUser}"
        )]
    return super().get_permissions()
```

### Using Permission Utilities

```python
from accounts.permission_utils import accounts_permissions, normalize_permissions

# Using the builder
permissions = accounts_permissions.permissions(
    "ManageAccountUser",
    "ViewResidents"
)

# Using normalization
permissions = normalize_permissions([
    AccountsPermissions.ManageAccountUser,
    "accounts.viewresidents"
])
```

### Advanced Configuration

```python
from accounts.permissions import HasSpecificPermission

class SecurityViewSet(ModelViewSet):
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [HasSpecificPermission(
                permissions=[
                    f"security.{SecurityPermissions.ViewSecurityLog}",
                    f"security.{SecurityPermissions.ViewSecurityAlert}"
                ],
                allow_safe_methods=True,
                allow_staff=True,
                allow_cluster_admin=True
            )]
        elif self.action in ['create', 'update', 'destroy']:
            return [HasSpecificPermission(
                permissions=[
                    f"security.{SecurityPermissions.ManageSecurityLog}",
                    f"security.{SecurityPermissions.ManageSecurityAlert}"
                ],
                allow_safe_methods=False,
                check_ownership=False  # Security logs might not have owners
            )]
        return super().get_permissions()
```

## Migration Guide

### From Old `HasClusterPermission`

**Before:**
```python
class MyViewSet(ModelViewSet):
    permission_classes = [
        HasClusterPermission(AccessControlPermissions.ManageVisitRequest)
    ]
```

**After:**
```python
class MyViewSet(ModelViewSet):
    permission_classes = [
        HasClusterPermission(
            permission=f"accesscontrol.{AccessControlPermissions.ManageVisitRequest}",
            allow_safe_methods=True
        )
    ]
```

### From Custom Permission Classes

**Before:**
```python
class CustomPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user.is_staff or user.is_cluster_admin:
            return True
        return user.has_perm("accounts.manageaccountuser")
```

**After:**
```python
from accounts.permissions import HasSpecificPermission

class MyViewSet(ModelViewSet):
    permission_classes = [
        HasSpecificPermission(
            permissions=["accounts.manageaccountuser"],
            allow_staff=True,
            allow_cluster_admin=True
        )
    ]
```

## Benefits of the New System

### 1. **Type Safety**
- Type hints throughout
- IDE autocomplete support
- Compile-time error detection

### 2. **Maintainability**
- No string manipulation
- Consistent patterns
- Reusable utilities

### 3. **Flexibility**
- Multiple permission support
- Configurable behavior
- Easy to extend

### 4. **Consistency**
- Unified base class
- Standardized patterns
- Predictable behavior

### 5. **Developer Experience**
- Better error messages
- Clear documentation
- Easy to test

## Testing

The new permission system is easier to test:

```python
from accounts.permissions import HasSpecificPermission
from core.common.permissions import AccountsPermissions

def test_permission_class():
    permission = HasSpecificPermission(
        permissions=[f"accounts.{AccountsPermissions.ManageAccountUser}"]
    )
    
    # Test with different user types
    assert permission.has_permission(staff_request, view) == True
    assert permission.has_permission(regular_user_request, view) == False
    assert permission.has_permission(admin_request, view) == True
```

## Best Practices

### 1. **Use Permission Constants**
```python
# Good
permission=f"accounts.{AccountsPermissions.ManageAccountUser}"

# Avoid
permission="accounts.manageaccountuser"
```

### 2. **Use Utilities for Complex Cases**
```python
# Good
from accounts.permission_utils import normalize_permissions
permissions = normalize_permissions([AccountsPermissions.ManageAccountUser])

# Avoid
permissions = ["accounts.manageaccountuser"]
```

### 3. **Configure Based on Use Case**
```python
# For read-only operations
HasSpecificPermission(
    permissions=[...],
    allow_safe_methods=True,
    check_ownership=True
)

# For admin operations
HasSpecificPermission(
    permissions=[...],
    allow_safe_methods=False,
    check_ownership=False
)
```

### 4. **Use Descriptive Names**
```python
# Good
class CanManageUsers(HasSpecificPermission):
    def __init__(self):
        super().__init__(
            permissions=[f"accounts.{AccountsPermissions.ManageAccountUser}"],
            allow_safe_methods=True
        )

# Avoid
class UserPermission(HasSpecificPermission):
    def __init__(self):
        super().__init__(permissions=["accounts.manageaccountuser"])
```

## Conclusion

The improved permission system provides:
- **Better maintainability** through elimination of string manipulation
- **Type safety** with proper type hints
- **Consistency** through unified base classes
- **Flexibility** with configurable options
- **Developer experience** with utilities and clear patterns

This makes the codebase more robust, easier to maintain, and less prone to errors while providing better developer experience. 