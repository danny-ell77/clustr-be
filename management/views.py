"""
Views for the management app.
"""

import logging
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, permissions, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AccountUser, Role
from accounts.role_permissions import (
    CanManageUsers,
    CanManageRoles,
    CanManageAdminSettings
)
from core.common.error_utils import log_exception_with_context, audit_log
from core.common.decorators import audit_viewset
from core.common.error_utils import exception_to_response_mapper
from core.common.responses import error_response
from core.common.exceptions import ValidationException, ResourceNotFoundException

from management.filters import UserFilter, RoleFilter

logger = logging.getLogger('clustr')


@audit_viewset(resource_type='user')
class UserListView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating users.
    """
    permission_classes = [IsAuthenticated, CanManageUsers]
    serializer_class = None  # Will be set in get_serializer_class
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    ordering = ['-date_joined']
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff and superusers can see all users
        if user.is_staff or user.is_superuser:
            return AccountUser.objects.all()
        
        # Cluster admins can see all users in their clusters
        if user.is_cluster_admin:
            user_clusters = user.clusters.all()
            return AccountUser.objects.filter(clusters__in=user_clusters)
        
        # Owners can see their subusers
        if user.is_owner:
            return AccountUser.objects.filter(
                Q(owner=user) | Q(id=user.id)
            )
        
        # Other users with permission can see users in their clusters
        user_clusters = user.clusters.all()
        return AccountUser.objects.filter(clusters__in=user_clusters)
    
    def get_serializer_class(self):
        # Import here to avoid circular imports
        from accounts.serializers.users import (
            AccountSerializer,
            OwnerAccountSerializer,
            SubuserAccountSerializer,
            StaffAccountSerializer
        )
        
        # Use different serializers based on the request method
        if self.request.method == 'POST':
            user_type = self.request.data.get('user_type', 'SUB_USER')
            if user_type == 'STAFF':
                return StaffAccountSerializer
            else:
                return SubuserAccountSerializer
        else:
            return AccountSerializer
    
    @transaction.atomic
    @audit_log(event_type='user.create', resource_type='user')
    def perform_create(self, serializer):
        serializer.save()


@audit_viewset(resource_type='user')
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating and deleting users.
    """
    permission_classes = [IsAuthenticated, CanManageUsers]
    serializer_class = None  # Will be set in get_serializer_class
    lookup_field = 'pk'
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff and superusers can see all users
        if user.is_staff or user.is_superuser:
            return AccountUser.objects.all()
        
        # Cluster admins can see all users in their clusters
        if user.is_cluster_admin:
            user_clusters = user.clusters.all()
            return AccountUser.objects.filter(clusters__in=user_clusters)
        
        # Owners can see their subusers
        if user.is_owner:
            return AccountUser.objects.filter(
                Q(owner=user) | Q(id=user.id)
            )
        
        # Other users with permission can see users in their clusters
        user_clusters = user.clusters.all()
        return AccountUser.objects.filter(clusters__in=user_clusters)
    
    def get_serializer_class(self):
        # Import here to avoid circular imports
        from accounts.serializers.users import AccountSerializer
        return AccountSerializer
    
    @audit_log(event_type='user.update', resource_type='user')
    def perform_update(self, serializer):
        serializer.save()
    
    @audit_log(event_type='user.delete', resource_type='user')
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


@audit_viewset(resource_type='role')
class RoleListView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating roles.
    """
    permission_classes = [IsAuthenticated, CanManageRoles]
    serializer_class = None  # Will be set in get_serializer_class
    filter_backends = [DjangoFilterBackend]
    filterset_class = RoleFilter
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff and superusers can see all roles
        if user.is_staff or user.is_superuser:
            return Role.objects.all()
        
        # Cluster admins can see all roles in their clusters
        if user.is_cluster_admin:
            return Role.objects.filter(owner=user)
        
        # Owners can see their roles
        if user.is_owner:
            return Role.objects.filter(owner=user)
        
        # Other users with permission can see roles in their clusters
        return Role.objects.filter(owner=user.get_owner())
    
    def get_serializer_class(self):
        # Import here to avoid circular imports
        from accounts.serializers.roles import RoleSerializer
        return RoleSerializer
    
    @transaction.atomic
    @audit_log(event_type='role.create', resource_type='role')
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user.get_owner())


@audit_viewset(resource_type='role')
class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating and deleting roles.
    """
    permission_classes = [IsAuthenticated, CanManageRoles]
    serializer_class = None  # Will be set in get_serializer_class
    lookup_field = 'pk'
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff and superusers can see all roles
        if user.is_staff or user.is_superuser:
            return Role.objects.all()
        
        # Cluster admins can see all roles in their clusters
        if user.is_cluster_admin:
            return Role.objects.filter(owner=user)
        
        # Owners can see their roles
        if user.is_owner:
            return Role.objects.filter(owner=user)
        
        # Other users with permission can see roles in their clusters
        return Role.objects.filter(owner=user.get_owner())
    
    def get_serializer_class(self):
        # Import here to avoid circular imports
        from accounts.serializers.roles import RoleSerializer
        return RoleSerializer
    
    @audit_log(event_type='role.update', resource_type='role')
    def perform_update(self, serializer):
        serializer.save()
    
    @audit_log(event_type='role.delete', resource_type='role')
    def perform_destroy(self, instance):
        instance.delete()


class AssignRoleView(APIView):
    """
    API endpoint for assigning roles to users.
    """
    permission_classes = [IsAuthenticated, CanManageUsers, CanManageRoles]
    
    @audit_log(event_type='user.assign_role', resource_type='user')
    @exception_to_response_mapper({
        ValidationException: lambda exc: error_response("VALIDATION_ERROR", str(exc), 400),
        ResourceNotFoundException: lambda exc: error_response("RESOURCE_NOT_FOUND", str(exc), 404)
    })
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        role_ids = request.data.get('role_ids', [])
        
        if not user_id or not role_ids:
            raise ValidationException(_("User ID and role IDs are required."))
        
        try:
            # Get the user
            user = AccountUser.objects.get(id=user_id)
            
            # Check if the requesting user has permission to manage this user
            if not CanManageUsers().has_object_permission(request, self, user):
                return Response(
                    {"detail": _("You do not have permission to manage this user.")},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get the roles
            roles = Role.objects.filter(id__in=role_ids)
            
            # Check if all roles exist
            if len(roles) != len(role_ids):
                raise ValidationException(_("One or more roles do not exist."))
            
            # Check if the requesting user has permission to manage these roles
            for role in roles:
                if not CanManageRoles().has_object_permission(request, self, role):
                    return Response(
                        {"detail": _("You do not have permission to assign one or more of these roles.")},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Assign the roles
            user.groups.set(roles)
            
            return Response(
                {"detail": _("Roles assigned successfully.")},
                status=status.HTTP_200_OK
            )
            
        except AccountUser.DoesNotExist:
            raise ResourceNotFoundException(_("User not found."))
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise ValidationException(_("Failed to assign roles."))