"""
Serializers for invitation management.
"""

from rest_framework import serializers

from core.common.models import Invitation, Visitor
from core.common.serializers.visitor_serializers import VisitorSerializer


class InvitationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invitation model.
    """
    visitor_details = VisitorSerializer(source='visitor', read_only=True)
    
    class Meta:
        model = Invitation
        fields = [
            'id', 'visitor', 'visitor_details', 'title', 'description', 
            'start_date', 'end_date', 'recurrence_type', 'recurrence_days',
            'recurrence_day_of_month', 'status', 'created_by', 'revoked_by',
            'revoked_at', 'revocation_reason', 'created_at', 'last_modified_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'revoked_by', 'revoked_at', 
            'created_at', 'last_modified_at'
        ]


class InvitationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new invitation.
    """
    
    class Meta:
        model = Invitation
        fields = [
            'visitor', 'title', 'description', 'start_date', 'end_date',
            'recurrence_type', 'recurrence_days', 'recurrence_day_of_month'
        ]
    
    def validate(self, data):
        """
        Validate the invitation data.
        """
        # Ensure end_date is after start_date
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        # Validate recurrence_days for weekly recurrence
        if data.get('recurrence_type') == Invitation.RecurrenceType.WEEKLY:
            if not data.get('recurrence_days'):
                raise serializers.ValidationError({
                    'recurrence_days': 'Recurrence days must be specified for weekly recurrence.'
                })
            
            # Validate that recurrence_days contains valid day numbers (0-6)
            try:
                days = [int(day) for day in data['recurrence_days'].split(',')]
                for day in days:
                    if day < 0 or day > 6:
                        raise ValueError()
            except (ValueError, AttributeError):
                raise serializers.ValidationError({
                    'recurrence_days': 'Recurrence days must be comma-separated numbers between 0 and 6.'
                })
        
        # Validate recurrence_day_of_month for monthly recurrence
        if data.get('recurrence_type') == Invitation.RecurrenceType.MONTHLY:
            if not data.get('recurrence_day_of_month'):
                raise serializers.ValidationError({
                    'recurrence_day_of_month': 'Recurrence day of month must be specified for monthly recurrence.'
                })
            
            # Validate that recurrence_day_of_month is a valid day of month (1-31)
            if data['recurrence_day_of_month'] < 1 or data['recurrence_day_of_month'] > 31:
                raise serializers.ValidationError({
                    'recurrence_day_of_month': 'Recurrence day of month must be between 1 and 31.'
                })
        
        return data
    
    def create(self, validated_data):
        """
        Create a new invitation.
        """
        # The created_by field will be set in the view
        # The cluster field will be set automatically by the AbstractClusterModel
        return super().create(validated_data)


class InvitationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing invitation.
    """
    
    class Meta:
        model = Invitation
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'recurrence_type', 'recurrence_days', 'recurrence_day_of_month', 'status'
        ]
    
    def validate(self, data):
        """
        Validate the invitation data.
        """
        # Ensure end_date is after start_date if both are provided
        if 'end_date' in data and 'start_date' in data:
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        elif 'end_date' in data:
            # If only end_date is provided, compare with existing start_date
            if data['end_date'] < self.instance.start_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        # Validate recurrence_days for weekly recurrence
        recurrence_type = data.get('recurrence_type', self.instance.recurrence_type)
        if recurrence_type == Invitation.RecurrenceType.WEEKLY:
            recurrence_days = data.get('recurrence_days', self.instance.recurrence_days)
            if not recurrence_days:
                raise serializers.ValidationError({
                    'recurrence_days': 'Recurrence days must be specified for weekly recurrence.'
                })
            
            # Validate that recurrence_days contains valid day numbers (0-6)
            try:
                days = [int(day) for day in recurrence_days.split(',')]
                for day in days:
                    if day < 0 or day > 6:
                        raise ValueError()
            except (ValueError, AttributeError):
                raise serializers.ValidationError({
                    'recurrence_days': 'Recurrence days must be comma-separated numbers between 0 and 6.'
                })
        
        # Validate recurrence_day_of_month for monthly recurrence
        if recurrence_type == Invitation.RecurrenceType.MONTHLY:
            recurrence_day_of_month = data.get('recurrence_day_of_month', self.instance.recurrence_day_of_month)
            if not recurrence_day_of_month:
                raise serializers.ValidationError({
                    'recurrence_day_of_month': 'Recurrence day of month must be specified for monthly recurrence.'
                })
            
            # Validate that recurrence_day_of_month is a valid day of month (1-31)
            if recurrence_day_of_month < 1 or recurrence_day_of_month > 31:
                raise serializers.ValidationError({
                    'recurrence_day_of_month': 'Recurrence day of month must be between 1 and 31.'
                })
        
        return data


class InvitationRevokeSerializer(serializers.ModelSerializer):
    """
    Serializer for revoking an invitation.
    """
    
    class Meta:
        model = Invitation
        fields = ['revocation_reason']