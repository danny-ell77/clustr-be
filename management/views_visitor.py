"""
Views for visitor management in the management app.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from management.filters import VisitorFilter, VisitorLogFilter

from accounts.permissions import HasClusterPermission
from core.common.models import Visitor, VisitorLog
from core.common.permissions import AccessControlPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.visitor_serializers import (
    VisitorSerializer,
    VisitorCreateSerializer,
    VisitorUpdateSerializer,
    VisitorLogSerializer,
    VisitorLogCreateSerializer,
)
from core.common.utils.notification_utils import NotificationManager

@audit_viewset(resource_type='visitor')
class ManagementVisitorViewSet(ModelViewSet):
    """
    ViewSet for managing visitors in the management app.
    Allows administrators to view and manage all visitors in the estate.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(AccessControlPermissions.ManageVisitRequest),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VisitorFilter
    
    def get_queryset(self):
        """
        Return all visitors for the current cluster.
        """
        return Visitor.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return VisitorCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VisitorUpdateSerializer
        return VisitorSerializer
    
    def perform_create(self, serializer):
        """
        Create a new visitor and set the invited_by field to the current user.
        """
        serializer.save(invited_by=self.request.user.id)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """
        Check in a visitor.
        """
        visitor = self.get_object()
        
        # Update visitor status
        visitor.status = Visitor.Status.CHECKED_IN
        visitor.save()
        
        # Create visitor log entry
        log_data = {
            'visitor': visitor.id,
            'log_type': VisitorLog.LogType.CHECKED_IN,
            'notes': request.data.get('notes', '')
        }
        
        serializer = VisitorLogCreateSerializer(data=log_data)
        if serializer.is_valid():
            log = serializer.save(checked_in_by=request.user.id)
            
            # Send notification to the user who invited the visitor
            try:
                # In a real implementation, you would get the user's email from the database
                # For now, we'll just use a placeholder
                user_email = "user@example.com"  # This would be replaced with actual user email
                NotificationManager.send_visitor_arrival_notification(
                    user_email=user_email,
                    visitor_name=visitor.name,
                    access_code=visitor.access_code
                )
            except Exception as e:
                # Log the error but don't fail the check-in
                pass
            
            return Response(
                VisitorLogSerializer(log).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """
        Check out a visitor.
        """
        visitor = self.get_object()
        
        # Update visitor status
        visitor.status = Visitor.Status.CHECKED_OUT
        visitor.save()
        
        # Create visitor log entry
        log_data = {
            'visitor': visitor.id,
            'log_type': VisitorLog.LogType.CHECKED_OUT,
            'notes': request.data.get('notes', '')
        }
        
        serializer = VisitorLogCreateSerializer(data=log_data)
        if serializer.is_valid():
            log = serializer.save(checked_out_by=request.user.id)
            return Response(
                VisitorLogSerializer(log).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def validate_access_code(self, request, pk=None):
        """
        Validate a visitor's access code.
        """
        visitor = self.get_object()
        access_code = request.data.get('access_code', '')
        
        if visitor.access_code == access_code:
            return Response({'valid': True}, status=status.HTTP_200_OK)
        return Response({'valid': False}, status=status.HTTP_400_BAD_REQUEST)


@audit_viewset(resource_type='visitor_log')
class ManagementVisitorLogViewSet(ModelViewSet):
    """
    ViewSet for managing visitor logs in the management app.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(AccessControlPermissions.ManageVisitRequest),
    ]
    serializer_class = VisitorLogSerializer
    
    def get_queryset(self):
        """
        Return all visitor logs for the current cluster.
        """
        return VisitorLog.objects.all()