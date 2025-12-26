"""
Task management views for ClustR management app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from management.filters import TaskFilter, TaskCommentFilter

from core.common.models import (
    Task, TaskComment, TaskAttachment, TaskStatus, TaskType, TaskPriority
)
from core.common.serializers.task_serializers import (
    TaskListSerializer, TaskDetailSerializer, TaskCreateSerializer,
    TaskUpdateSerializer, TaskAssignmentRequestSerializer,
    TaskStatusUpdateSerializer, TaskEscalationRequestSerializer,
    TaskCommentCreateSerializer, TaskCommentSerializer,
    TaskStatisticsSerializer, TaskFileUploadSerializer
)
from core.common.includes import notifications, tasks
from accounts.models import AccountUser
from accounts.permissions import IsClusterStaffOrAdmin


class ManagementTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tasks in the management app.
    Provides full CRUD operations and task management functionality.
    """
    
    permission_classes = [IsAuthenticated, IsClusterStaffOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get tasks for the current cluster."""
        if getattr(self, "swagger_fake_view", False):
            return Task.objects.none()

        return Task.objects.filter(cluster=getattr(self.request, "cluster_context", None)).select_related(
            'assigned_to', 'created_by', 'escalated_to'
        ).prefetch_related(
            'attachments', 'comments', 'status_history', 'escalation_history'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TaskListSerializer
        elif self.action in ['create']:
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        else:
            return TaskDetailSerializer
    
    def perform_create(self, serializer):
        """Create a new task."""
        assigned_to = None
        if 'assigned_to_id' in serializer.validated_data:
            assigned_to_id = serializer.validated_data.pop('assigned_to_id')
            if assigned_to_id:
                assigned_to = get_object_or_404(
                    AccountUser, 
                    id=assigned_to_id, 
                    clusters=getattr(self.request, "cluster_context", None)
                )
        
        task = tasks.create(
            created_by=self.request.user,
            cluster=getattr(self.request, "cluster_context", None),
            assigned_to=assigned_to,
            **serializer.validated_data
        )
        
        serializer.instance = task
    
    def perform_update(self, serializer):
        """Update a task."""
        if 'assigned_to_id' in serializer.validated_data:
            assigned_to_id = serializer.validated_data.pop('assigned_to_id')
            if assigned_to_id:
                assigned_to = get_object_or_404(
                    AccountUser, 
                    id=assigned_to_id, 
                    clusters=getattr(self.request, "cluster_context", None)
                )
                if serializer.instance.assigned_to != assigned_to:
                    tasks.assign(
                        serializer.instance, 
                        assigned_to, 
                        self.request.user
                    )
        
        serializer.save(last_modified_by=self.request.user.id)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign a task to a user."""
        task = self.get_object()
        serializer = TaskAssignmentRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            assigned_to = get_object_or_404(
                AccountUser, 
                id=serializer.validated_data['assigned_to_id'],
                clusters=request.cluster_context
            )
            
            success = tasks.assign(task, assigned_to, request.user)
            
            if success:
                return Response({
                    'message': f'Task assigned to {assigned_to.name}',
                    'task': TaskDetailSerializer(task).data
                })
            else:
                return Response(
                    {'error': 'Failed to assign task'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update task status."""
        task = self.get_object()
        serializer = TaskStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            notes = serializer.validated_data.get('notes', '')
            completion_notes = serializer.validated_data.get('completion_notes', '')
            actual_hours = serializer.validated_data.get('actual_hours')
            
            old_status = task.status
            
            try:
                if new_status == TaskStatus.IN_PROGRESS:
                    tasks.start(task, request.user)
                elif new_status == TaskStatus.COMPLETED:
                    if actual_hours:
                        task.actual_hours = actual_hours
                    tasks.complete(task, completion_notes, request.user)
                elif new_status == TaskStatus.CANCELLED:
                    task.cancel_task(notes, request.user)
                else:
                    task.status = new_status
                    task.notes = f"{task.notes}\n\n{notes}".strip() if notes else task.notes
                    task.save()
                
                return Response({
                    'message': f'Task status updated to {new_status}',
                    'task': TaskDetailSerializer(task).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate a task."""
        task = self.get_object()
        serializer = TaskEscalationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            escalated_to = get_object_or_404(
                AccountUser, 
                id=serializer.validated_data['escalated_to_id'],
                clusters=request.cluster_context
            )
            
            success = tasks.escalate(
                task, 
                escalated_to, 
                serializer.validated_data['reason'], 
                request.user
            )
            
            if success:
                return Response({
                    'message': f'Task escalated to {escalated_to.name}',
                    'task': TaskDetailSerializer(task).data
                })
            else:
                return Response(
                    {'error': 'Failed to escalate task'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue tasks."""
        overdue_tasks = tasks.get_overdue(request.cluster_context)
        serializer = TaskListSerializer(overdue_tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get tasks due soon."""
        # This action can be handled by the filterset if a 'due_soon' method is added to TaskFilter
        # For now, keeping the existing logic as it uses TaskManager
        hours = int(request.query_params.get('hours', 24))
        due_soon_tasks = tasks.get_due_soon(request.cluster_context, hours)
        serializer = TaskListSerializer(due_soon_tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get task statistics."""
        stats = tasks.get_statistics(request.cluster_context)
        serializer = TaskStatisticsSerializer(stats)
        return Response(serializer.data)
    
    
    
    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        """Upload a file attachment to a task."""
        task = self.get_object()
        serializer = TaskFileUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                file_url = tasks.upload_attachment(
                    task,
                    serializer.validated_data['file'],
                    request.user,
                    serializer.validated_data['attachment_type']
                )
                
                return Response({
                    'message': 'File uploaded successfully',
                    'file_url': file_url
                })
                
            except Exception as e:
                return Response(
                    {'error': f'Failed to upload file: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def complete_with_evidence(self, request, pk=None):
        """Complete a task with evidence attachments."""
        task = self.get_object()
        
        # Check if task can be completed
        if task.status != TaskStatus.IN_PROGRESS:
            return Response(
                {'error': 'Task must be in progress to be completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        completion_notes = request.data.get('completion_notes', '')
        actual_hours = request.data.get('actual_hours')
        evidence_files = request.FILES.getlist('evidence_files')
        
        # Validate evidence files if provided
        if evidence_files:
            validation_result = tasks.validate_evidence_files(evidence_files)
            if not validation_result['valid']:
                return Response(
                    {'error': 'Invalid evidence files', 'details': validation_result['errors']}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            # Update actual hours if provided
            if actual_hours:
                task.actual_hours = float(actual_hours)
                task.save()
            
            # Complete the task with evidence
            success = tasks.complete(
                task=task,
                completion_notes=completion_notes,
                completed_by=request.user,
                evidence_files=evidence_files
            )
            
            if success:
                # Get completion evidence for response
                evidence_attachments = tasks.get_completion_evidence(task)
                
                return Response({
                    'message': 'Task completed successfully',
                    'task': TaskDetailSerializer(task).data,
                    'evidence_count': len(evidence_attachments),
                    'evidence_files': [
                        {
                            'file_name': att.file_name,
                            'file_url': att.file_url,
                            'file_size': att.file_size,
                            'uploaded_at': att.created_at
                        }
                        for att in evidence_attachments
                    ]
                })
            else:
                return Response(
                    {'error': 'Failed to complete task'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'error': f'Failed to complete task: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def performance_analytics(self, request):
        """Get task performance analytics."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                parsed_end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        analytics = tasks.get_performance_analytics(
            cluster=request.cluster_context,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        return Response(analytics)


class ManagementTaskCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task comments in the management app.
    """
    
    permission_classes = [IsAuthenticated, IsClusterStaffOrAdmin]
    serializer_class = TaskCommentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskCommentFilter
    ordering = ['created_at']
    
    def get_queryset(self):
        """Get comments for tasks in the current cluster."""
        if getattr(self, "swagger_fake_view", False):
            return TaskComment.objects.none()

        return TaskComment.objects.filter(
            task__cluster=getattr(self.request, "cluster_context", None)
        ).select_related('author', 'task', 'parent')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCommentCreateSerializer
        return TaskCommentSerializer
    
    def perform_create(self, serializer):
        """Create a new task comment."""
        task_id = self.request.data.get('task_id')
        if not task_id:
            raise serializers.ValidationError({'task_id': 'This field is required.'})
        
        task = get_object_or_404(
            Task, 
            id=task_id, 
            cluster=getattr(self.request, "cluster_context", None)
        )
        
        serializer.save(
            author=self.request.user,
            task=task,
            cluster=getattr(self.request, "cluster_context", None)
        )
        
        # Send notification about new comment
        tasks.send_comment_notification(
            serializer.instance, task
        )
    
    def perform_update(self, serializer):
        """Update a task comment."""
        serializer.save(last_modified_by=self.request.user.id)
    
    