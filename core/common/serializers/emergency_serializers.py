"""
Serializers for emergency management models.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.common.models.emergency import (
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
    EmergencyStatus,
)


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Serializer for EmergencyContact model"""
    
    emergency_types_display = serializers.SerializerMethodField()
    contact_type_display = serializers.CharField(source='get_contact_type_display', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id',
            'name',
            'phone_number',
            'email',
            'emergency_types',
            'emergency_types_display',
            'contact_type',
            'contact_type_display',
            'user',
            'user_name',
            'is_active',
            'is_primary',
            'response_time_minutes',
            'notes',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'last_modified_at']

    def get_emergency_types_display(self, obj):
        """Get display names for emergency types"""
        return obj.get_emergency_types_display()

    def validate_emergency_types(self, value):
        """Validate emergency types"""
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Emergency types must be a list"))
        
        valid_types = [choice[0] for choice in EmergencyType.choices]
        for emergency_type in value:
            if emergency_type not in valid_types:
                raise serializers.ValidationError(
                    _("Invalid emergency type: {}").format(emergency_type)
                )
        
        return value

    def validate(self, data):
        """Validate the emergency contact data"""
        # Ensure estate-wide contacts don't have a user
        if data.get('contact_type') == EmergencyContactType.ESTATE_WIDE and data.get('user'):
            raise serializers.ValidationError(
                _("Estate-wide contacts cannot be associated with a specific user")
            )
        
        # Ensure personal contacts have a user
        if data.get('contact_type') == EmergencyContactType.PERSONAL and not data.get('user'):
            raise serializers.ValidationError(
                _("Personal contacts must be associated with a user")
            )
        
        return data


class EmergencyContactCreateSerializer(EmergencyContactSerializer):
    """Serializer for creating emergency contacts"""
    
    class Meta(EmergencyContactSerializer.Meta):
        fields = [
            'name',
            'phone_number',
            'email',
            'emergency_types',
            'contact_type',
            'user',
            'is_active',
            'is_primary',
            'response_time_minutes',
            'notes',
        ]


class EmergencyContactUpdateSerializer(EmergencyContactSerializer):
    """Serializer for updating emergency contacts"""
    
    class Meta(EmergencyContactSerializer.Meta):
        fields = [
            'name',
            'phone_number',
            'email',
            'emergency_types',
            'is_active',
            'is_primary',
            'response_time_minutes',
            'notes',
        ]


class SOSAlertSerializer(serializers.ModelSerializer):
    """Serializer for SOSAlert model"""
    
    emergency_type_display = serializers.CharField(source='get_emergency_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.name', read_only=True)
    responded_by_name = serializers.CharField(source='responded_by.name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True)
    cancelled_by_name = serializers.CharField(source='cancelled_by.name', read_only=True)
    response_time_minutes = serializers.ReadOnlyField()
    resolution_time_minutes = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = SOSAlert
        fields = [
            'id',
            'alert_id',
            'user',
            'user_name',
            'emergency_type',
            'emergency_type_display',
            'description',
            'location',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'acknowledged_at',
            'acknowledged_by',
            'acknowledged_by_name',
            'responded_at',
            'responded_by',
            'responded_by_name',
            'resolved_at',
            'resolved_by',
            'resolved_by_name',
            'resolution_notes',
            'cancelled_at',
            'cancelled_by',
            'cancelled_by_name',
            'cancellation_reason',
            'response_time_minutes',
            'resolution_time_minutes',
            'is_active',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = [
            'id', 'alert_id', 'acknowledged_at', 'acknowledged_by',
            'responded_at', 'responded_by', 'resolved_at', 'resolved_by',
            'cancelled_at', 'cancelled_by', 'created_at', 'last_modified_at'
        ]


class SOSAlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SOS alerts"""
    
    class Meta:
        model = SOSAlert
        fields = [
            'emergency_type',
            'description',
            'location',
            'priority',
        ]

    def validate_emergency_type(self, value):
        """Validate emergency type"""
        valid_types = [choice[0] for choice in EmergencyType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(_("Invalid emergency type"))
        return value


class SOSAlertUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating SOS alerts"""
    
    class Meta:
        model = SOSAlert
        fields = [
            'description',
            'location',
            'priority',
            'resolution_notes',
            'cancellation_reason',
        ]


class EmergencyResponseSerializer(serializers.ModelSerializer):
    """Serializer for EmergencyResponse model"""
    
    alert_id = serializers.CharField(source='alert.alert_id', read_only=True)
    responder_name = serializers.CharField(source='responder.name', read_only=True)
    response_type_display = serializers.CharField(source='get_response_type_display', read_only=True)
    
    class Meta:
        model = EmergencyResponse
        fields = [
            'id',
            'alert',
            'alert_id',
            'responder',
            'responder_name',
            'response_type',
            'response_type_display',
            'notes',
            'estimated_arrival',
            'actual_arrival',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'last_modified_at']


class EmergencyResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating emergency responses"""
    
    class Meta:
        model = EmergencyResponse
        fields = [
            'alert',
            'response_type',
            'notes',
            'estimated_arrival',
            'actual_arrival',
        ]


class EmergencyTypeChoicesSerializer(serializers.Serializer):
    """Serializer for emergency type choices"""
    
    value = serializers.CharField()
    label = serializers.CharField()


class EmergencyContactTypeChoicesSerializer(serializers.Serializer):
    """Serializer for emergency contact type choices"""
    
    value = serializers.CharField()
    label = serializers.CharField()


class EmergencyStatusChoicesSerializer(serializers.Serializer):
    """Serializer for emergency status choices"""
    
    value = serializers.CharField()
    label = serializers.CharField()


class EmergencyStatsSerializer(serializers.Serializer):
    """Serializer for emergency statistics"""
    
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    resolved_alerts = serializers.IntegerField()
    cancelled_alerts = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    alerts_by_type = serializers.DictField()
    alerts_by_status = serializers.DictField()


class EmergencyReportSerializer(serializers.Serializer):
    """Serializer for emergency reports"""
    
    report_generated_at = serializers.DateTimeField()
    filters = serializers.DictField()
    summary = serializers.DictField()
    time_analysis = serializers.DictField()
    responder_analysis = serializers.DictField()
    recent_alerts = serializers.ListField()


class IncidentReportSerializer(serializers.Serializer):
    """Serializer for incident reports"""
    
    alert_info = serializers.DictField()
    timeline = serializers.ListField()
    metrics = serializers.DictField()
    involved_contacts = serializers.ListField()
    responses_summary = serializers.DictField()
    report_generated_at = serializers.DateTimeField()


class EmergencyReportFiltersSerializer(serializers.Serializer):
    """Serializer for emergency report filters"""
    
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    emergency_type = serializers.ChoiceField(
        choices=EmergencyType.choices,
        required=False
    )
    status = serializers.ChoiceField(
        choices=EmergencyStatus.choices,
        required=False
    )