"""
Serializers for visitor management.
"""

from rest_framework import serializers

from core.common.models import Visitor, VisitorLog


class VisitorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Visitor model.
    """
    
    class Meta:
        model = Visitor
        fields = [
            'id', 'name', 'email', 'phone', 'estimated_arrival', 'visit_type',
            'access_code', 'invited_by', 'status', 'valid_for', 'valid_date',
            'purpose', 'notes', 'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'access_code', 'created_at', 'last_modified_at']


class VisitorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new visitor.
    """
    
    class Meta:
        model = Visitor
        fields = [
            'name', 'email', 'phone', 'estimated_arrival', 'visit_type',
            'valid_for', 'valid_date', 'purpose', 'notes'
        ]
    
    def create(self, validated_data):
        # The invited_by field will be set in the view
        # The cluster field will be set automatically by the AbstractClusterModel
        return super().create(validated_data)


class VisitorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing visitor.
    """
    
    class Meta:
        model = Visitor
        fields = [
            'name', 'email', 'phone', 'estimated_arrival', 'visit_type',
            'status', 'valid_for', 'valid_date', 'purpose', 'notes'
        ]
        read_only_fields = ['access_code']


class VisitorLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the VisitorLog model.
    """
    visitor_name = serializers.CharField(source='visitor.name', read_only=True)
    
    class Meta:
        model = VisitorLog
        fields = [
            'id', 'visitor', 'visitor_name', 'date', 'arrival_time', 
            'departure_time', 'log_type', 'checked_in_by', 'checked_out_by',
            'notes', 'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'date', 'created_at', 'last_modified_at']


class VisitorLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new visitor log entry.
    """
    
    class Meta:
        model = VisitorLog
        fields = ['visitor', 'arrival_time', 'departure_time', 'log_type', 'notes']