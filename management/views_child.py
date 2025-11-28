"""
Views for child security management in the management app.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from management.filters import ChildFilter, ExitRequestFilter, EntryExitLogFilter
from django.utils import timezone

from accounts.permissions import HasClusterPermission
from core.common.models import Child, ExitRequest, EntryExitLog
from core.common.permissions import AccessControlPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.child_serializers import (
    ChildSerializer,
    ChildCreateSerializer,
    ChildUpdateSerializer,
    ExitRequestSerializer,
    ExitRequestCreateSerializer,
    ExitRequestUpdateSerializer,
    ExitRequestApprovalSerializer,
    EntryExitLogSerializer,
    EntryExitLogCreateSerializer,
    EntryExitLogUpdateSerializer,
    EntryExitActionSerializer,
)
from core.common.includes.file_storage import FileStorage
from core.notifications.events import NotificationEvents
from core.common.includes import notifications


@audit_viewset(resource_type='child')
class ManagementChildViewSet(ModelViewSet):
    """
    ViewSet for managing children in the management app.
    Allows administrators to view and manage all children in the estate.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageVisitRequest]),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ChildFilter
    
    def get_queryset(self):
        """
        Return all children for the current cluster.
        """
        return Child.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return ChildCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ChildUpdateSerializer
        return ChildSerializer
    
    def perform_create(self, serializer):
        """
        Create a new child. The parent field must be provided in the request.
        """
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        """
        Upload a profile photo for the child.
        """
        child = self.get_object()
        
        if 'photo' not in request.FILES:
            return Response(
                {'error': 'No photo file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        photo_file = request.FILES['photo']
        
        try:
            # Upload the file using the file storage utility
            photo_url = FileStorage.upload_file(
                photo_file,
                folder='child_profiles',
                cluster_id=str(request.cluster_context.id) if hasattr(request, 'cluster_context') else None
            )
            
            # Update the child's profile photo
            child.profile_photo = photo_url
            child.save(update_fields=['profile_photo'])
            
            return Response(
                {'profile_photo': photo_url},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to upload photo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def by_parent(self, request):
        """
        Get children filtered by parent ID.
        """
        children = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)


@audit_viewset(resource_type='exit_request')
class ManagementExitRequestViewSet(ModelViewSet):
    """
    ViewSet for managing exit requests in the management app.
    Allows administrators to view, approve, and deny exit requests.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageVisitRequest]),
    ]
    
    def get_queryset(self):
        """
        Return all exit requests for the current cluster.
        """
        return ExitRequest.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return ExitRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExitRequestUpdateSerializer
        elif self.action == 'approve_deny':
            return ExitRequestApprovalSerializer
        return ExitRequestSerializer
    
    def perform_create(self, serializer):
        """
        Create a new exit request. The requested_by field must be provided.
        """
        # Set default expiration time if not provided (24 hours from now)
        if 'expires_at' not in serializer.validated_data:
            serializer.validated_data['expires_at'] = timezone.now() + timezone.timedelta(hours=24)
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def approve_deny(self, request, pk=None):
        """
        Approve or deny an exit request.
        """
        exit_request = self.get_object()
        serializer = ExitRequestApprovalSerializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            reason = serializer.validated_data.get('reason', '')
            
            if action == 'approve':
                success = exit_request.approve(request.user)
                if success:
                    # Create an entry/exit log for the approved request
                    log_data = {
                        'child': exit_request.child,
                        'exit_request': exit_request,
                        'log_type': EntryExitLog.LogType.EXIT,
                        'date': timezone.now().date(),
                        'expected_return_time': exit_request.expected_return_time,
                        'reason': exit_request.reason,
                        'destination': exit_request.destination,
                        'accompanying_adult': exit_request.accompanying_adult,
                        'status': EntryExitLog.Status.SCHEDULED,
                    }
                    
                    EntryExitLog.objects.create(**log_data)
                    
                    # Send notification to parent
                    try:
                        notifications.send(
                            event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for EXIT_REQUEST_APPROVED
                            recipients=[exit_request.requested_by],
                            cluster=exit_request.cluster,
                            context={
                                "request_id": exit_request.request_id,
                                "child_name": exit_request.child.name,
                                "approved_by_name": request.user.name,
                                "expected_return_time": exit_request.expected_return_time.strftime('%Y-%m-%d %H:%M'),
                            }
                        )
                    except Exception as e:
                        # Log the error but don't fail the approval
                        pass
                    
                    return Response({'status': 'exit request approved'}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {'error': 'Cannot approve this request'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            elif action == 'deny':
                success = exit_request.deny(request.user, reason)
                if success:
                    # Send notification to parent
                    try:
                        notifications.send(
                            event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for EXIT_REQUEST_DENIED
                            recipients=[exit_request.requested_by],
                            cluster=exit_request.cluster,
                            context={
                                "request_id": exit_request.request_id,
                                "child_name": exit_request.child.name,
                                "denied_by_name": request.user.name,
                                "denial_reason": reason,
                            }
                        )
                    except Exception as e:
                        # Log the error but don't fail the denial
                        pass
                    
                    return Response({'status': 'exit request denied'}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {'error': 'Cannot deny this request'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get all pending exit requests.
        """
        pending_requests = self.get_queryset().filter(status=ExitRequest.Status.PENDING)
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get all expired exit requests.
        """
        expired_requests = self.get_queryset().filter(
            status=ExitRequest.Status.PENDING,
            expires_at__lt=timezone.now()
        )
        
        # Mark them as expired
        expired_requests.update(status=ExitRequest.Status.EXPIRED)
        
        serializer = self.get_serializer(expired_requests, many=True)
        return Response(serializer.data)


@audit_viewset(resource_type='entry_exit_log')
class ManagementEntryExitLogViewSet(ModelViewSet):
    """
    ViewSet for managing entry/exit logs in the management app.
    Allows administrators to view and manage all entry/exit logs.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageVisitRequest]),
    ]
    
    def get_queryset(self):
        """
        Return all entry/exit logs for the current cluster.
        """
        return EntryExitLog.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return EntryExitLogCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EntryExitLogUpdateSerializer
        elif self.action in ['mark_exit', 'mark_entry', 'mark_overdue']:
            return EntryExitActionSerializer
        return EntryExitLogSerializer
    
    @action(detail=True, methods=['post'])
    def mark_exit(self, request, pk=None):
        """
        Mark a child as having exited.
        """
        log = self.get_object()
        serializer = EntryExitActionSerializer(data=request.data)
        
        if serializer.is_valid():
            success = log.mark_exit(verified_by=request.user)
            if success:
                if serializer.validated_data.get('notes'):
                    log.notes = serializer.validated_data['notes']
                    log.save(update_fields=['notes'])
                
                # Send notification to parent
                try:
                    notifications.send(
                        event=NotificationEvents.CHILD_EXIT_ALERT,
                        recipients=[log.child.parent],
                        cluster=log.cluster,
                        context={
                            "child_name": log.child.name,
                            "exit_time": log.exit_time.strftime('%H:%M') if log.exit_time else 'Unknown',
                            "expected_return_time": log.expected_return_time.strftime('%Y-%m-%d %H:%M') if log.expected_return_time else 'Not specified',
                            "destination": log.destination,
                            "accompanying_adult": log.accompanying_adult,
                        }
                    )
                except Exception as e:
                    # Log the error but don't fail the action
                    pass
                
                return Response(
                    EntryExitLogSerializer(log).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Cannot mark exit for this log'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_entry(self, request, pk=None):
        """
        Mark a child as having returned.
        """
        log = self.get_object()
        serializer = EntryExitActionSerializer(data=request.data)
        
        if serializer.is_valid():
            success = log.mark_entry(verified_by=request.user)
            if success:
                if serializer.validated_data.get('notes'):
                    log.notes = serializer.validated_data['notes']
                    log.save(update_fields=['notes'])
                
                # Send notification to parent
                try:
                    notifications.send(
                        event=NotificationEvents.CHILD_ENTRY_ALERT,
                        recipients=[log.child.parent],
                        cluster=log.cluster,
                        context={
                            "child_name": log.child.name,
                            "entry_time": log.entry_time.strftime('%H:%M') if log.entry_time else 'Unknown',
                            "duration_minutes": log.duration_minutes,
                        }
                    )
                except Exception as e:
                    # Log the error but don't fail the action
                    pass
                
                return Response(
                    EntryExitLogSerializer(log).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Cannot mark entry for this log'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_overdue(self, request, pk=None):
        """
        Mark a child as overdue.
        """
        log = self.get_object()
        success = log.mark_overdue()
        
        if success:
            # Send overdue notification to parent and administrators
            try:
                recipients = []
                if log.child.parent:
                    recipients.append(log.child.parent)
                # Add cluster admins
                from accounts.models import AccountUser
                cluster_admins = AccountUser.objects.filter(
                    clusters=log.cluster,
                    is_cluster_admin=True
                )
                recipients.extend(list(cluster_admins))

                notifications.send(
                    event=NotificationEvents.CHILD_OVERDUE_ALERT,
                    recipients=recipients,
                    cluster=log.cluster,
                    context={
                        "child_name": log.child.name,
                        "parent_name": log.child.parent.name if log.child.parent else "N/A",
                        "expected_return_time": log.expected_return_time.strftime('%Y-%m-%d %H:%M'),
                        "overdue_minutes": int((timezone.now() - log.expected_return_time).total_seconds() / 60),
                        "destination": log.destination,
                        "accompanying_adult": log.accompanying_adult,
                        "parent_phone": log.child.parent.phone_number if log.child.parent else "N/A",
                    }
                )
            except Exception as e:
                # Log the error but don't fail the action
                pass
            
            return Response(
                EntryExitLogSerializer(log).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Cannot mark this log as overdue'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get all overdue children.
        """
        overdue_logs = self.get_queryset().filter(status=EntryExitLog.Status.OVERDUE)
        serializer = self.get_serializer(overdue_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active_exits(self, request):
        """
        Get all active exits (children currently out).
        """
        active_exits = self.get_queryset().filter(
            log_type=EntryExitLog.LogType.EXIT,
            status=EntryExitLog.Status.IN_PROGRESS
        )
        serializer = self.get_serializer(active_exits, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_overdue(self, request):
        """
        Check for overdue children and mark them as overdue.
        """
        from django.utils import timezone
        
        # Find logs that should be marked as overdue
        potentially_overdue = self.get_queryset().filter(
            log_type=EntryExitLog.LogType.EXIT,
            status=EntryExitLog.Status.IN_PROGRESS,
            expected_return_time__lt=timezone.now()
        )
        
        overdue_count = 0
        for log in potentially_overdue:
            if log.mark_overdue():
                overdue_count += 1
                
                # Send overdue notification
                try:
                    from core.common.includes import notifications
                    from core.notifications.events import NotificationEvents
                    
                    recipients = [log.child.parent] if log.child.parent else []
                    if recipients:
                        notifications.send(
                            event=NotificationEvents.CHILD_OVERDUE_ALERT,
                            recipients=recipients,
                            cluster=log.cluster,
                            context={
                                'child_name': log.child.name,
                                'location': log.location or 'Unknown location',
                                'expected_return_time': log.expected_return_time.strftime('%H:%M') if log.expected_return_time else 'Not specified',
                                'overdue_minutes': (timezone.now() - log.expected_return_time).total_seconds() / 60 if log.expected_return_time else 0,
                                'parent_name': log.child.parent.name if log.child.parent else 'Parent',
                            }
                        )
                except Exception as e:
                    # Log the error but continue processing
                    logger.error(f"Failed to send child overdue notification: {e}")
        
        return Response(
            {'message': f'{overdue_count} children marked as overdue'},
            status=status.HTTP_200_OK
        )