"""
Serializers for shift management in ClustR application.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from core.common.models import Shift, ShiftSwapRequest, ShiftAttendance, ShiftType, ShiftStatus
from accounts.models import AccountUser


class StaffSummarySerializer(serializers.ModelSerializer):
    """Serializer for staff summary information."""
    
    class Meta:
        model = AccountUser
        fields = ['id', 'name', 'email_address', 'phone_number']
        read_only_fields = ['id', 'name', 'email_address', 'phone_number']


class ShiftAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for shift attendance information."""
    
    actual_work_duration_hours = serializers.SerializerMethodField()
    overtime_hours_decimal = serializers.SerializerMethodField()
    
    class Meta:
        model = ShiftAttendance
        fields = [
            'clock_in_time',
            'clock_out_time',
            'break_start_time',
            'break_end_time',
            'total_break_duration',
            'overtime_hours',
            'overtime_hours_decimal',
            'late_arrival_minutes',
            'early_departure_minutes',
            'actual_work_duration_hours',
            'attendance_notes'
        ]
        read_only_fields = [
            'overtime_hours',
            'late_arrival_minutes',
            'early_departure_minutes'
        ]
    
    def get_actual_work_duration_hours(self, obj):
        """Get actual work duration in hours."""
        duration = obj.actual_work_duration
        return round(duration.total_seconds() / 3600, 2) if duration else 0
    
    def get_overtime_hours_decimal(self, obj):
        """Get overtime hours as decimal."""
        return round(obj.overtime_hours.total_seconds() / 3600, 2) if obj.overtime_hours else 0


class ShiftSerializer(serializers.ModelSerializer):
    """Serializer for shift information."""
    
    assigned_staff_details = StaffSummarySerializer(source='assigned_staff', read_only=True)
    attendance = ShiftAttendanceSerializer(read_only=True)
    duration_hours = serializers.SerializerMethodField()
    actual_duration_hours = serializers.SerializerMethodField()
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    shift_type_display = serializers.CharField(source='get_shift_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Shift
        fields = [
            'id',
            'title',
            'shift_type',
            'shift_type_display',
            'assigned_staff',
            'assigned_staff_details',
            'start_time',
            'end_time',
            'actual_start_time',
            'actual_end_time',
            'status',
            'status_display',
            'location',
            'responsibilities',
            'notes',
            'is_recurring',
            'recurrence_pattern',
            'duration_hours',
            'actual_duration_hours',
            'is_overdue',
            'is_upcoming',
            'attendance',
            'created_at',
            'last_modified_at'
        ]
        read_only_fields = [
            'id',
            'actual_start_time',
            'actual_end_time',
            'status',
            'created_at',
            'last_modified_at'
        ]
    
    def get_duration_hours(self, obj):
        """Get scheduled duration in hours."""
        duration = obj.duration
        return round(duration.total_seconds() / 3600, 2) if duration else 0
    
    def get_actual_duration_hours(self, obj):
        """Get actual duration in hours."""
        duration = obj.actual_duration
        return round(duration.total_seconds() / 3600, 2) if duration else 0
    
    def validate(self, data):
        """Validate shift data."""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("Start time must be before end time")
            
            # Check if start time is in the past (for new shifts)
            if not self.instance and start_time < timezone.now():
                raise serializers.ValidationError("Cannot schedule shifts in the past")
        
        return data


class ShiftCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shifts."""
    
    class Meta:
        model = Shift
        fields = [
            'title',
            'shift_type',
            'assigned_staff',
            'start_time',
            'end_time',
            'location',
            'responsibilities',
            'notes',
            'is_recurring',
            'recurrence_pattern'
        ]
    
    def validate(self, data):
        """Validate shift creation data."""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        assigned_staff = data.get('assigned_staff')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("Start time must be before end time")
            
            if start_time < timezone.now():
                raise serializers.ValidationError("Cannot schedule shifts in the past")
        
        # Check for conflicts (this will be handled in the view using ShiftManager)
        return data


class ShiftUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shifts."""
    
    class Meta:
        model = Shift
        fields = [
            'title',
            'shift_type',
            'assigned_staff',
            'start_time',
            'end_time',
            'location',
            'responsibilities',
            'notes',
            'is_recurring',
            'recurrence_pattern'
        ]
    
    def validate(self, data):
        """Validate shift update data."""
        start_time = data.get('start_time', self.instance.start_time)
        end_time = data.get('end_time', self.instance.end_time)
        
        if start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")
        
        # Only allow updates to scheduled shifts
        if self.instance.status != ShiftStatus.SCHEDULED:
            raise serializers.ValidationError("Can only update scheduled shifts")
        
        return data


class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    """Serializer for shift swap requests."""
    
    original_shift_details = ShiftSerializer(source='original_shift', read_only=True)
    target_shift_details = ShiftSerializer(source='target_shift', read_only=True)
    requested_by_details = StaffSummarySerializer(source='requested_by', read_only=True)
    requested_with_details = StaffSummarySerializer(source='requested_with', read_only=True)
    approved_by_details = StaffSummarySerializer(source='approved_by', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ShiftSwapRequest
        fields = [
            'id',
            'original_shift',
            'original_shift_details',
            'requested_by',
            'requested_by_details',
            'requested_with',
            'requested_with_details',
            'target_shift',
            'target_shift_details',
            'reason',
            'status',
            'status_display',
            'approved_by',
            'approved_by_details',
            'approved_at',
            'response_message',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'status',
            'approved_by',
            'approved_at',
            'created_at'
        ]


class ShiftSwapRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shift swap requests."""
    
    class Meta:
        model = ShiftSwapRequest
        fields = [
            'original_shift',
            'requested_with',
            'target_shift',
            'reason'
        ]
    
    def validate(self, data):
        """Validate swap request data."""
        original_shift = data.get('original_shift')
        target_shift = data.get('target_shift')
        requested_with = data.get('requested_with')
        
        if original_shift.status != ShiftStatus.SCHEDULED:
            raise serializers.ValidationError("Can only swap scheduled shifts")
        
        if target_shift and target_shift.status != ShiftStatus.SCHEDULED:
            raise serializers.ValidationError("Can only swap with scheduled shifts")
        
        if target_shift and target_shift.assigned_staff != requested_with:
            raise serializers.ValidationError("Target shift must be assigned to the person you're swapping with")
        
        return data


class ShiftSwapResponseSerializer(serializers.Serializer):
    """Serializer for responding to shift swap requests."""
    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    response_message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_action(self, value):
        """Validate the action."""
        if value not in ['approve', 'reject']:
            raise serializers.ValidationError("Action must be 'approve' or 'reject'")
        return value


class ClockInOutSerializer(serializers.Serializer):
    """Serializer for clock in/out operations."""
    
    timestamp = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_timestamp(self, value):
        """Validate timestamp."""
        if value and value > timezone.now():
            raise serializers.ValidationError("Cannot clock in/out in the future")
        return value


class ShiftStatisticsSerializer(serializers.Serializer):
    """Serializer for shift statistics."""
    
    total_shifts = serializers.IntegerField()
    completed_shifts = serializers.IntegerField()
    no_show_shifts = serializers.IntegerField()
    cancelled_shifts = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    average_overtime_hours = serializers.FloatField()


class ShiftListSerializer(serializers.ModelSerializer):
    """Simplified serializer for shift lists."""
    
    assigned_staff_name = serializers.CharField(source='assigned_staff.name', read_only=True)
    shift_type_display = serializers.CharField(source='get_shift_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Shift
        fields = [
            'id',
            'title',
            'shift_type',
            'shift_type_display',
            'assigned_staff_name',
            'start_time',
            'end_time',
            'status',
            'status_display',
            'location',
            'duration_hours',
            'is_overdue',
            'is_upcoming'
        ]
    
    def get_duration_hours(self, obj):
        """Get duration in hours."""
        duration = obj.duration
        return round(duration.total_seconds() / 3600, 2) if duration else 0