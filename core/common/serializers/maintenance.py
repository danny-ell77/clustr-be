"""
Serializers for maintenance models.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.common.models import (
    MaintenanceLog, MaintenanceAttachment, MaintenanceSchedule,
    MaintenanceCost, MaintenanceComment, MaintenanceType,
    MaintenanceStatus, MaintenancePriority, PropertyType
)
from accounts.serializers import AccountSerializer


class MaintenanceLogSerializer(serializers.ModelSerializer):
    """Serializer for MaintenanceLog model."""
    
    performed_by = AccountSerializer(read_only=True)
    supervised_by = AccountSerializer(read_only=True)
    requested_by = AccountSerializer(read_only=True)
    
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    is_overdue = serializers.ReadOnlyField()
    is_due_soon = serializers.ReadOnlyField()
    time_remaining = serializers.ReadOnlyField()
    duration_worked = serializers.ReadOnlyField()
    
    attachments_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceLog
        fields = [
            'id', 'maintenance_number', 'title', 'description',
            'maintenance_type', 'maintenance_type_display',
            'property_type', 'property_type_display',
            'property_location', 'equipment_name',
            'priority', 'priority_display',
            'status', 'status_display',
            'performed_by', 'supervised_by', 'requested_by', 'related_ticket',
            'scheduled_date', 'started_at', 'completed_at',
            'estimated_duration', 'actual_duration',
            'cost', 'materials_used', 'tools_used',
            'notes', 'completion_notes',
            'next_maintenance_due', 'warranty_expiry', 'is_under_warranty',
            'is_overdue', 'is_due_soon', 'time_remaining', 'duration_worked',
            'attachments_count', 'comments_count', 'total_cost',
            'created_at', 'last_modified_at'
        ]
        read_only_fields = [
            'id', 'maintenance_number', 'is_overdue', 'is_due_soon',
            'time_remaining', 'duration_worked', 'attachments_count',
            'comments_count', 'total_cost', 'created_at', 'last_modified_at'
        ]
    
    def get_attachments_count(self, obj):
        """Get the number of attachments."""
        return obj.attachments.count()
    
    def get_comments_count(self, obj):
        """Get the number of comments."""
        return obj.comments.count()
    
    def get_total_cost(self, obj):
        """Get the total cost including breakdown."""
        if obj.cost:
            return float(obj.cost)
        # Calculate from cost breakdown if main cost is not set
        total = sum(cost.total_cost for cost in obj.cost_breakdown.all())
        return float(total)


class MaintenanceLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating MaintenanceLog."""
    
    class Meta:
        model = MaintenanceLog
        fields = [
            'title', 'description', 'maintenance_type', 'property_type',
            'property_location', 'equipment_name', 'priority',
            'scheduled_date', 'estimated_duration', 'cost',
            'materials_used', 'tools_used', 'notes',
            'next_maintenance_due', 'warranty_expiry', 'related_ticket'
        ]
    
    def validate_scheduled_date(self, value):
        """Validate scheduled date."""
        if value and value <= timezone.now():
            raise serializers.ValidationError(_("Scheduled date must be in the future"))
        return value


class MaintenanceLogUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating MaintenanceLog."""
    
    class Meta:
        model = MaintenanceLog
        fields = [
            'title', 'description', 'maintenance_type', 'property_type',
            'property_location', 'equipment_name', 'priority', 'status',
            'scheduled_date', 'estimated_duration', 'actual_duration',
            'cost', 'materials_used', 'tools_used', 'notes',
            'completion_notes', 'next_maintenance_due', 'warranty_expiry', 'related_ticket'
        ]


class MaintenanceAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for MaintenanceAttachment model."""
    
    uploaded_by = AccountSerializer(read_only=True)
    attachment_type_display = serializers.CharField(source='get_attachment_type_display', read_only=True)
    
    class Meta:
        model = MaintenanceAttachment
        fields = [
            'id', 'file_name', 'file_url', 'file_size', 'file_type',
            'attachment_type', 'attachment_type_display',
            'description', 'uploaded_by', 'created_at'
        ]
        read_only_fields = ['id', 'file_url', 'file_size', 'file_type', 'created_at']


class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    """Serializer for MaintenanceSchedule model."""
    
    assigned_to = AccountSerializer(read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    frequency_type_display = serializers.CharField(source='get_frequency_type_display', read_only=True)
    
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'id', 'name', 'description',
            'property_type', 'property_type_display',
            'property_location', 'equipment_name',
            'frequency_type', 'frequency_type_display', 'frequency_value',
            'next_due_date', 'estimated_duration', 'estimated_cost',
            'assigned_to', 'is_active',
            'instructions', 'materials_needed', 'tools_needed',
            'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_modified_at']


class MaintenanceScheduleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating MaintenanceSchedule."""
    
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'name', 'description', 'property_type', 'property_location',
            'equipment_name', 'frequency_type', 'frequency_value',
            'next_due_date', 'estimated_duration', 'estimated_cost',
            'instructions', 'materials_needed', 'tools_needed'
        ]


class MaintenanceCostSerializer(serializers.ModelSerializer):
    """Serializer for MaintenanceCost model."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = MaintenanceCost
        fields = [
            'id', 'category', 'category_display', 'description',
            'quantity', 'unit_cost', 'total_cost',
            'vendor', 'receipt_number', 'date_incurred',
            'created_at'
        ]
        read_only_fields = ['id', 'total_cost', 'created_at']


class MaintenanceCommentSerializer(serializers.ModelSerializer):
    """Serializer for MaintenanceComment model."""
    
    author = AccountSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceComment
        fields = [
            'id', 'content', 'is_internal', 'author',
            'parent', 'replies', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_replies(self, obj):
        """Get replies to this comment."""
        if obj.replies.exists():
            return MaintenanceCommentSerializer(obj.replies.all(), many=True).data
        return []


class MaintenanceCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating MaintenanceComment."""
    
    class Meta:
        model = MaintenanceComment
        fields = ['content', 'is_internal', 'parent']


class MaintenanceSummarySerializer(serializers.Serializer):
    """Serializer for maintenance summary data."""
    
    total_maintenance = serializers.IntegerField()
    completed_maintenance = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    total_cost = serializers.FloatField()
    average_cost = serializers.FloatField()
    by_type = serializers.DictField()
    by_property = serializers.DictField()
    by_status = serializers.DictField()
    frequent_locations = serializers.ListField()
    average_duration = serializers.DurationField(allow_null=True)


class MaintenanceOptimizationSerializer(serializers.Serializer):
    """Serializer for maintenance optimization suggestions."""
    
    type = serializers.CharField()
    message = serializers.CharField()
    priority = serializers.CharField()


class MaintenanceHistorySerializer(serializers.ModelSerializer):
    """Simplified serializer for maintenance history."""
    
    performed_by_name = serializers.CharField(source='performed_by.name', read_only=True)
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MaintenanceLog
        fields = [
            'id', 'maintenance_number', 'title',
            'maintenance_type', 'maintenance_type_display',
            'status', 'status_display',
            'performed_by_name', 'cost',
            'scheduled_date', 'completed_at', 'created_at'
        ]