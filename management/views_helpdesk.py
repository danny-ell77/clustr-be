"""
Management views for help desk system.
"""

from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from core.common.decorators import audit_viewset
from core.common.models.helpdesk import (
    IssueTicket,
    IssueComment,
    IssueAttachment,
    IssueStatus,
    IssueType,
    IssuePriority,
)
from core.common.serializers.helpdesk import (
    IssueTicketListSerializer,
    IssueTicketDetailSerializer,
    IssueTicketUpdateSerializer,
    IssueCommentSerializer,
    IssueCommentCreateSerializer,
    IssueAttachmentSerializer,
    IssueAttachmentCreateSerializer,
)
from core.notifications.events import NotificationEvents
from core.common.includes import notifications
from core.common.includes.file_storage import FileStorage
from accounts.permissions import IsClusterStaffOrAdmin
from core.common.includes import maintenance
from core.common.serializers.maintenance import MaintenanceLogSerializer
from core.common.models import MaintenanceStatus
from core.common.error_codes import CommonAPIErrorCodes
from core.common.responses import error_response

class ManagementIssueTicketFilter(django_filters.FilterSet):
    """Filter for management issue tickets"""
    status = django_filters.CharFilter(field_name='status')
    type = django_filters.CharFilter(field_name='issue_type')
    priority = django_filters.CharFilter(field_name='priority')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = IssueTicket
        fields = ['status', 'type', 'priority', 'assigned_to', 'date_from', 'date_to']


@audit_viewset(resource_type='issue_ticket')
class ManagementIssueTicketViewSet(ModelViewSet):
    """
    Management viewset for issue tickets.
    Allows administrators to view and manage all issues in their cluster.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ManagementIssueTicketFilter
    
    def get_queryset(self):
        """Get all issues in the cluster with search functionality"""
        if getattr(self, "swagger_fake_view", False):
            return IssueTicket.objects.none()

        queryset = IssueTicket.objects.filter(
            cluster=self.request.cluster_context
        ).select_related(
            'reported_by',
            'assigned_to',
            'cluster'
        ).prefetch_related(
            'comments',
            'attachments',
            'status_history'
        )
        
        
        
        # Order by priority and creation date
        return queryset.order_by(
            Case(
                When(priority=IssuePriority.URGENT, then=1),
                When(priority=IssuePriority.HIGH, then=2),
                When(priority=IssuePriority.MEDIUM, then=3),
                When(priority=IssuePriority.LOW, then=4),
                output_field=IntegerField(),
            ),
            '-created_at'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return IssueTicketListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return IssueTicketUpdateSerializer
        else:
            return IssueTicketDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """List all issues with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update issue ticket"""
        instance = self.get_object()
        old_assigned_to = instance.assigned_to
        
        response = super().update(request, *args, **kwargs)
        
        # Send assignment notification if assigned_to changed
        new_assigned_to = instance.assigned_to
        if old_assigned_to != new_assigned_to and new_assigned_to:
            notifications.send(
                event=NotificationEvents.ISSUE_ASSIGNED,
                recipients=[new_assigned_to],
                cluster=instance.cluster,
                context={
                    "issue_number": instance.issue_no,
                    "issue_title": instance.title,
                    "assigned_to_name": new_assigned_to.name,
                }
            )
        
        return response
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign issue to a staff member"""
        issue: IssueTicket = self.get_object()
        assigned_to_id = request.data.get('assigned_to')
        from accounts.models import AccountUser

        try:
            assigned_to = AccountUser.objects.get(
                id=assigned_to_id,
                clusters=request.cluster_context,
                is_cluster_staff=True
            )
        except AccountUser.DoesNotExist:
            return Response(
                {'error': 'Invalid staff member'},
                status=status.HTTP_400_BAD_REQUEST
            )

        issue.assign(assigned_to)        
        serializer = self.get_serializer(issue)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate an issue"""
        issue = self.get_object()
        issue.escalte()
        
        serializer = self.get_serializer(issue)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_maintenance(self, request, pk=None):
        """
        Create a maintenance log from this issue ticket.
        """
        issue = self.get_object()
        
        # Check if maintenance log already exists
        if issue.maintenance_logs.exists():
             return error_response(
                error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                message="Maintenance log already exists for this ticket",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        property_location = request.data.get('property_location')
        if not property_location:
            return error_response(
                error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                message="property_location is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Map issue type to property type
        from core.common.models.maintenance.property import PropertyType as MaintenancePropertyType
        from core.common.models.helpdesk import IssueType

        # Default mapping
        property_type_mapping = {
            IssueType.PLUMBING: MaintenancePropertyType.PLUMBING,
            IssueType.ELECTRICAL: MaintenancePropertyType.ELECTRICAL,
            IssueType.SECURITY: MaintenancePropertyType.SECURITY,
            IssueType.CARPENTRY: MaintenancePropertyType.BUILDING,
            IssueType.CLEANING: MaintenancePropertyType.BUILDING,
            IssueType.OTHER: MaintenancePropertyType.OTHER,
        }
        
        # Determine property type: 
        # 1. Explicitly provided in request
        # 2. Mapped from issue type
        # 3. Default to OTHER
        property_type = request.data.get('property_type')
        if not property_type:
            property_type = property_type_mapping.get(issue.issue_type, MaintenancePropertyType.OTHER)
            
        try:
            # Prepare maintenance log data
            maintenance_log = maintenance.create_log(
                cluster=request.cluster_context,
                requested_by=issue.reported_by,
                title=f"From Ticket #{issue.issue_no}: {issue.title}",
                description=issue.description,
                priority=issue.priority, 
                property_location=property_location,
                related_ticket=issue,
                property_type=property_type,
                maintenance_type=request.data.get('maintenance_type', 'CORRECTIVE'),
                status=MaintenanceStatus.SCHEDULED
            )
            
            # Update issue status
            issue.status = IssueStatus.IN_PROGRESS
            issue.save()
            
            serializer = MaintenanceLogSerializer(maintenance_log)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            from core.common.includes.logging import logger
            logger.error(f"Error creating maintenance from issue {issue.id}: {str(e)}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to create maintenance log",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get issue statistics for dashboard"""
        queryset = self.get_queryset()
        
        stats = {
            'total_issues': queryset.count(),
            'open_issues': queryset.filter(status__in=[
                IssueStatus.SUBMITTED,
                IssueStatus.OPEN,
                IssueStatus.IN_PROGRESS,
                IssueStatus.PENDING
            ]).count(),
            'resolved_issues': queryset.filter(status=IssueStatus.RESOLVED).count(),
            'closed_issues': queryset.filter(status=IssueStatus.CLOSED).count(),
            'escalated_issues': queryset.filter(escalated_at__isnull=False).count(),
            'overdue_issues': queryset.filter(
                due_date__lt=timezone.now(),
                status__in=[
                    IssueStatus.SUBMITTED,
                    IssueStatus.OPEN,
                    IssueStatus.IN_PROGRESS,
                    IssueStatus.PENDING
                ]
            ).count(),
        }
        
        # Issues by type
        issues_by_type = queryset.values('issue_type').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['issues_by_type'] = list(issues_by_type)
        
        # Issues by priority
        issues_by_priority = queryset.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['issues_by_priority'] = list(issues_by_priority)
        
        return Response(stats)


@audit_viewset(resource_type='issue_comment')
class ManagementIssueCommentViewSet(ModelViewSet):
    """
    Management viewset for issue comments.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    serializer_class = IssueCommentSerializer
    
    def get_queryset(self):
        """Get comments for a specific issue"""
        if getattr(self, "swagger_fake_view", False):
            return IssueComment.objects.none()

        issue_id = self.kwargs.get('issue_pk')
        return IssueComment.objects.filter(
            issue_id=issue_id,
            
        ).select_related('author').prefetch_related('attachments', 'replies')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return IssueCommentCreateSerializer
        return IssueCommentSerializer
    
    def get_serializer_context(self):
        """Add issue_id to serializer context"""
        context = super().get_serializer_context()
        context['issue_id'] = self.kwargs.get('issue_pk')
        return context
    
    def list(self, request, *args, **kwargs):
        """List comments for an issue"""
        # Only show top-level comments, replies are included in the serializer
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@audit_viewset(resource_type='issue_attachment')
class ManagementIssueAttachmentViewSet(ModelViewSet):
    """
    Management viewset for issue attachments.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    serializer_class = IssueAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Get attachments for a specific issue or comment"""
        if getattr(self, "swagger_fake_view", False):
            return IssueAttachment.objects.none()

        issue_id = self.kwargs.get('issue_pk')
        comment_id = self.kwargs.get('comment_pk')
        
        queryset = IssueAttachment.objects.filter(
            
        )
        
        if comment_id:
            queryset = queryset.filter(comment_id=comment_id)
        elif issue_id:
            queryset = queryset.filter(issue_id=issue_id)
        
        return queryset.select_related('uploaded_by')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return IssueAttachmentCreateSerializer
        return IssueAttachmentSerializer
    
    def get_serializer_context(self):
        """Add issue_id and comment_id to serializer context"""
        context = super().get_serializer_context()
        context['issue_id'] = self.kwargs.get('issue_pk')
        context['comment_id'] = self.kwargs.get('comment_pk')
        return context
    
    def create(self, request, *args, **kwargs):
        """Upload and create attachment"""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Upload file using FileStorage utility
        file_storage = FileStorage()
        file_url = file_storage.upload_file(
            file_obj,
            folder='helpdesk/attachments'
        )
        
        # Create attachment record
        serializer_data = {
            'file_name': file_obj.name,
            'file_url': file_url,
            'file_size': file_obj.size,
            'file_type': file_obj.content_type,
        }
        
        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)