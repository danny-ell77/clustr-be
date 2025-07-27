"""
Task serializers for ClustR application.
"""

from rest_framework import serializers
from django.utils import timezone

from core.common.models import (
    Task, TaskAssignment, TaskAttachment, TaskComment,
    TaskStatusHistory, TaskEscalationHistory, TaskType, TaskStatus, TaskPriority
)
from accounts.serializers import UserSummarySerializer


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for task attachments."""
    
    uploaded_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'file_name', 'file_url', 'file_size', 'file_type',
            'attachment_type', 'uploaded_by', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments."""
    
    author = UserSummarySerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskComment
        fields = [
            'id', 'content', 'author', 'is_internal', 'parent',
            'replies', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        """Get replies to this comment."""
        if obj.replies.exists():
            return TaskCommentSerializer(obj.replies.all(), many=True).data
        return []


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for task status history."""
    
    changed_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = TaskStatusHistory
        fields = [
            'id', 'from_status', 'to_status', 'changed_by',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TaskEscalationHistorySerializer(serializers.ModelSerializer):
    """Serializer for task escalation history."""
    
    escalated_to = UserSummarySerializer(read_only=True)
    escalated_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = TaskEscalationHistory
        fields = [
            'id', 'escalated_to', 'escalated_by', 'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TaskAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for task assignments."""
    
    assigned_to = UserSummarySerializer(read_only=True)
    assigned_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = TaskAssignment
        fields = [
            'id', 'assigned_to', 'assigned_by', 'assigned_at', 'notes'
        ]
        read_only_fields = ['id', 'assigned_at']


class TaskListSerializer(serializers.ModelSerializer):
    """Serializer for task list view."""
    
    assigned_to = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    escalated_to = UserSummarySerializer(read_only=True)
    
    # Computed fields
    is_overdue = serializers.ReadOnlyField()
    is_due_soon = serializers.ReadOnlyField()
    time_remaining = serializers.SerializerMethodField()
    duration_worked = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'title', 'task_type', 'priority', 'status',
            'assigned_to', 'created_by', 'due_date', 'location',
            'estimated_hours', 'actual_hours', 'escalated_to', 'escalated_at',
            'started_at', 'completed_at', 'created_at', 'updated_at',
            'is_overdue', 'is_due_soon', 'time_remaining', 'duration_worked'
        ]
        read_only_fields = [
            'id', 'task_number', 'created_by', 'started_at', 'completed_at',
            'escalated_at', 'escalated_to', 'created_at', 'updated_at'
        ]
    
    def get_time_remaining(self, obj):
        """Get time remaining until due date."""
        if obj.time_remaining:
            total_seconds = int(obj.time_remaining.total_seconds())
            if total_seconds < 0:
                return "Overdue"
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    def get_duration_worked(self, obj):
        """Get duration worked on the task."""
        duration = obj.duration_worked
        if duration and duration.total_seconds() > 0:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "0h 0m"


class TaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed task view."""
    
    assigned_to = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    escalated_to = UserSummarySerializer(read_only=True)
    
    # Related data
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    status_history = TaskStatusHistorySerializer(many=True, read_only=True)
    escalation_history = TaskEscalationHistorySerializer(many=True, read_only=True)
    assignment_history = serializers.SerializerMethodField()
    
    # Computed fields
    is_overdue = serializers.ReadOnlyField()
    is_due_soon = serializers.ReadOnlyField()
    time_remaining = serializers.SerializerMethodField()
    duration_worked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'title', 'description', 'task_type',
            'priority', 'status', 'assigned_to', 'created_by', 'due_date',
            'started_at', 'completed_at', 'estimated_hours', 'actual_hours',
            'location', 'notes', 'completion_notes', 'escalated_at',
            'escalated_to', 'created_at', 'updated_at',
            'attachments', 'comments', 'status_history', 'escalation_history',
            'assignment_history', 'is_overdue', 'is_due_soon', 'time_remaining',
            'duration_worked', 'comments_count'
        ]
        read_only_fields = [
            'id', 'task_number', 'created_by', 'started_at', 'completed_at',
            'escalated_at', 'escalated_to', 'created_at', 'updated_at'
        ]
    
    def get_assignment_history(self, obj):
        """Get assignment history for the task."""
        return TaskAssignmentSerializer(obj.assignment_history.all(), many=True).data
    
    def get_time_remaining(self, obj):
        """Get time remaining until due date."""
        if obj.time_remaining:
            total_seconds = int(obj.time_remaining.total_seconds())
            if total_seconds < 0:
                return "Overdue"
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    def get_duration_worked(self, obj):
        """Get duration worked on the task."""
        duration = obj.duration_worked
        if duration and duration.total_seconds() > 0:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "0h 0m"
    
    def get_comments_count(self, obj):
        """Get the number of comments on this task."""
        return obj.comments.count()


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks."""
    
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'task_type', 'priority', 'assigned_to_id',
            'due_date', 'estimated_hours', 'location', 'notes'
        ]
    
    def validate_due_date(self, value):
        """Validate that due date is in the future."""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Due date must be in the future.")
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Estimated hours must be positive.")
        return value


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tasks."""
    
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'task_type', 'priority', 'assigned_to_id',
            'due_date', 'estimated_hours', 'actual_hours', 'location', 'notes'
        ]
    
    def validate_due_date(self, value):
        """Validate that due date is in the future."""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Due date must be in the future.")
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Estimated hours must be positive.")
        return value
    
    def validate_actual_hours(self, value):
        """Validate actual hours."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Actual hours must be positive.")
        return value


class TaskAssignmentRequestSerializer(serializers.Serializer):
    """Serializer for task assignment requests."""
    
    assigned_to_id = serializers.UUIDField()
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Serializer for task status updates."""
    
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    completion_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    actual_hours = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)


class TaskEscalationRequestSerializer(serializers.Serializer):
    """Serializer for task escalation requests."""
    
    escalated_to_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=1000)


class TaskCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating task comments."""
    
    class Meta:
        model = TaskComment
        fields = ['content', 'is_internal', 'parent']
    
    def validate_content(self, value):
        """Validate comment content."""
        if not value.strip():
            raise serializers.ValidationError("Comment content cannot be empty.")
        return value.strip()


class TaskStatisticsSerializer(serializers.Serializer):
    """Serializer for task statistics."""
    
    total_tasks = serializers.IntegerField()
    status_breakdown = serializers.DictField()
    priority_breakdown = serializers.DictField()
    type_breakdown = serializers.DictField()
    overdue_tasks = serializers.IntegerField()
    due_soon_tasks = serializers.IntegerField()
    average_completion_hours = serializers.FloatField(allow_null=True)


class TaskFileUploadSerializer(serializers.Serializer):
    """Serializer for task file uploads."""
    
    file = serializers.FileField()
    attachment_type = serializers.ChoiceField(
        choices=[
            ('INSTRUCTION', 'Instruction'),
            ('REFERENCE', 'Reference'),
            ('EVIDENCE', 'Evidence'),
            ('COMPLETION', 'Completion'),
            ('OTHER', 'Other'),
        ],
        default='OTHER'
    )
    
    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB.")
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain', 'text/csv'
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("File type not supported.")
        
        return value