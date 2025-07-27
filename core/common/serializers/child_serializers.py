"""
Serializers for child security management.
"""

from rest_framework import serializers
from django.utils import timezone

from core.common.models import Child, ExitRequest, EntryExitLog


class ChildSerializer(serializers.ModelSerializer):
    """
    Serializer for the Child model.
    """
    age = serializers.ReadOnlyField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    emergency_contacts_display = serializers.ReadOnlyField(source='get_emergency_contacts_display')
    
    class Meta:
        model = Child
        fields = [
            'id', 'name', 'date_of_birth', 'gender', 'profile_photo',
            'house_number', 'parent', 'parent_name', 'emergency_contacts',
            'emergency_contacts_display', 'is_active', 'notes', 'age',
            'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_modified_at']


class ChildCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new child.
    """
    
    class Meta:
        model = Child
        fields = [
            'name', 'date_of_birth', 'gender', 'profile_photo',
            'house_number', 'emergency_contacts', 'notes'
        ]
    
    def validate_date_of_birth(self, value):
        """Validate that the date of birth is not in the future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
    def validate_emergency_contacts(self, value):
        """Validate emergency contacts format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Emergency contacts must be a list.")
        
        for contact in value:
            if not isinstance(contact, dict):
                raise serializers.ValidationError("Each emergency contact must be an object.")
            
            required_fields = ['name', 'phone', 'relationship']
            for field in required_fields:
                if field not in contact or not contact[field]:
                    raise serializers.ValidationError(f"Emergency contact must have a {field}.")
        
        return value
    
    def create(self, validated_data):
        # The parent field will be set in the view
        # The cluster field will be set automatically by the AbstractClusterModel
        return super().create(validated_data)


class ChildUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing child.
    """
    
    class Meta:
        model = Child
        fields = [
            'name', 'date_of_birth', 'gender', 'profile_photo',
            'house_number', 'emergency_contacts', 'is_active', 'notes'
        ]
    
    def validate_date_of_birth(self, value):
        """Validate that the date of birth is not in the future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
    def validate_emergency_contacts(self, value):
        """Validate emergency contacts format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Emergency contacts must be a list.")
        
        for contact in value:
            if not isinstance(contact, dict):
                raise serializers.ValidationError("Each emergency contact must be an object.")
            
            required_fields = ['name', 'phone', 'relationship']
            for field in required_fields:
                if field not in contact or not contact[field]:
                    raise serializers.ValidationError(f"Emergency contact must have a {field}.")
        
        return value


class ExitRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for the ExitRequest model.
    """
    child_name = serializers.CharField(source='child.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.name', read_only=True)
    denied_by_name = serializers.CharField(source='denied_by.name', read_only=True)
    is_expired = serializers.ReadOnlyField()
    is_pending = serializers.ReadOnlyField()
    
    class Meta:
        model = ExitRequest
        fields = [
            'id', 'request_id', 'child', 'child_name', 'requested_by',
            'requested_by_name', 'reason', 'expected_return_time', 'destination',
            'accompanying_adult', 'accompanying_adult_phone', 'status',
            'approved_by', 'approved_by_name', 'approved_at', 'denied_by',
            'denied_by_name', 'denied_at', 'denial_reason', 'expires_at',
            'is_expired', 'is_pending', 'created_at', 'last_modified_at'
        ]
        read_only_fields = [
            'id', 'request_id', 'approved_by', 'approved_at', 'denied_by',
            'denied_at', 'denial_reason', 'created_at', 'last_modified_at'
        ]


class ExitRequestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new exit request.
    """
    
    class Meta:
        model = ExitRequest
        fields = [
            'child', 'reason', 'expected_return_time', 'destination',
            'accompanying_adult', 'accompanying_adult_phone', 'expires_at'
        ]
    
    def validate_expected_return_time(self, value):
        """Validate that expected return time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Expected return time must be in the future.")
        return value
    
    def validate_expires_at(self, value):
        """Validate that expiration time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Expiration time must be in the future.")
        return value
    
    def validate(self, data):
        """Validate that expiration time is after expected return time"""
        if data.get('expires_at') and data.get('expected_return_time'):
            if data['expires_at'] <= data['expected_return_time']:
                raise serializers.ValidationError(
                    "Expiration time must be after expected return time."
                )
        return data
    
    def create(self, validated_data):
        # The requested_by field will be set in the view
        # The cluster field will be set automatically by the AbstractClusterModel
        return super().create(validated_data)


class ExitRequestUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing exit request.
    """
    
    class Meta:
        model = ExitRequest
        fields = [
            'reason', 'expected_return_time', 'destination',
            'accompanying_adult', 'accompanying_adult_phone', 'expires_at'
        ]
    
    def validate_expected_return_time(self, value):
        """Validate that expected return time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Expected return time must be in the future.")
        return value
    
    def validate_expires_at(self, value):
        """Validate that expiration time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Expiration time must be in the future.")
        return value
    
    def validate(self, data):
        """Validate that expiration time is after expected return time"""
        if data.get('expires_at') and data.get('expected_return_time'):
            if data['expires_at'] <= data['expected_return_time']:
                raise serializers.ValidationError(
                    "Expiration time must be after expected return time."
                )
        return data


class ExitRequestApprovalSerializer(serializers.Serializer):
    """
    Serializer for approving/denying exit requests.
    """
    action = serializers.ChoiceField(choices=['approve', 'deny'])
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate that reason is provided for denial"""
        if data.get('action') == 'deny' and not data.get('reason'):
            raise serializers.ValidationError("Reason is required when denying a request.")
        return data


class EntryExitLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the EntryExitLog model.
    """
    child_name = serializers.CharField(source='child.name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = EntryExitLog
        fields = [
            'id', 'child', 'child_name', 'exit_request', 'log_type', 'date',
            'exit_time', 'entry_time', 'expected_return_time', 'actual_return_time',
            'reason', 'destination', 'accompanying_adult', 'status',
            'verified_by', 'verified_by_name', 'notes', 'is_overdue',
            'duration_minutes', 'created_at', 'last_modified_at'
        ]
        read_only_fields = [
            'id', 'actual_return_time', 'created_at', 'last_modified_at'
        ]


class EntryExitLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new entry/exit log.
    """
    
    class Meta:
        model = EntryExitLog
        fields = [
            'child', 'exit_request', 'log_type', 'date', 'expected_return_time',
            'reason', 'destination', 'accompanying_adult', 'notes'
        ]
    
    def validate_date(self, value):
        """Validate that the date is not in the future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Log date cannot be in the future.")
        return value
    
    def validate_expected_return_time(self, value):
        """Validate that expected return time is in the future for exit logs"""
        if self.initial_data.get('log_type') == 'exit' and value:
            if value <= timezone.now():
                raise serializers.ValidationError("Expected return time must be in the future for exit logs.")
        return value


class EntryExitLogUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing entry/exit log.
    """
    
    class Meta:
        model = EntryExitLog
        fields = [
            'expected_return_time', 'reason', 'destination',
            'accompanying_adult', 'notes', 'status'
        ]


class EntryExitActionSerializer(serializers.Serializer):
    """
    Serializer for marking exit/entry actions.
    """
    action = serializers.ChoiceField(choices=['mark_exit', 'mark_entry', 'mark_overdue'])
    notes = serializers.CharField(required=False, allow_blank=True)