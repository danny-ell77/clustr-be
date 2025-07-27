"""
Serializers for event management.
"""

from rest_framework import serializers

from core.common.models import Event, EventGuest


class EventGuestSerializer(serializers.ModelSerializer):
    """
    Serializer for the EventGuest model.
    """
    
    class Meta:
        model = EventGuest
        fields = [
            'id', 'event', 'name', 'email', 'phone', 'access_code', 'invited_by',
            'status', 'notes', 'check_in_time', 'check_out_time', 'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'access_code', 'created_at', 'last_modified_at']


class EventGuestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new event guest.
    """
    
    class Meta:
        model = EventGuest
        fields = ['name', 'email', 'phone', 'notes']
    
    def create(self, validated_data):
        # The event, invited_by, and cluster fields will be set in the view
        return super().create(validated_data)


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """
    guests_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'event_date', 'event_time', 'end_time',
            'location', 'access_code', 'max_guests', 'guests_added', 'created_by',
            'status', 'is_public', 'requires_approval', 'guests_count',
            'created_at', 'last_modified_at'
        ]
        read_only_fields = ['id', 'access_code', 'guests_added', 'created_at', 'last_modified_at']
    
    def get_guests_count(self, obj):
        """
        Get the number of guests for this event.
        """
        return obj.guests.count()


class EventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new event.
    """
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_date', 'event_time', 'end_time',
            'location', 'max_guests', 'status', 'is_public', 'requires_approval'
        ]
    
    def validate(self, data):
        """
        Validate the event data.
        """
        # Ensure end_time is after event_time if both are provided
        if 'end_time' in data and 'event_time' in data:
            if data['end_time'] <= data['event_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after event time.'
                })
        
        return data
    
    def create(self, validated_data):
        # The created_by field will be set in the view
        # The cluster field will be set automatically by the AbstractClusterModel
        return super().create(validated_data)


class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing event.
    """
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_date', 'event_time', 'end_time',
            'location', 'max_guests', 'status', 'is_public', 'requires_approval'
        ]
    
    def validate(self, data):
        """
        Validate the event data.
        """
        # Ensure end_time is after event_time if both are provided
        if 'end_time' in data and 'event_time' in data:
            if data['end_time'] <= data['event_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after event time.'
                })
        elif 'end_time' in data and 'event_time' not in data:
            # If only end_time is provided, compare with existing event_time
            if data['end_time'] <= self.instance.event_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after event time.'
                })
        
        return data


class BulkGuestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating multiple guests at once.
    """
    guests = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of guests to add to the event"
    )
    
    def validate_guests(self, value):
        """
        Validate the list of guests.
        """
        for guest in value:
            # Ensure each guest has a name
            if 'name' not in guest or not guest['name']:
                raise serializers.ValidationError("Each guest must have a name.")
        
        return value


class EventGuestCheckInSerializer(serializers.Serializer):
    """
    Serializer for checking in an event guest.
    """
    notes = serializers.CharField(required=False, allow_blank=True)


class EventGuestCheckOutSerializer(serializers.Serializer):
    """
    Serializer for checking out an event guest.
    """
    notes = serializers.CharField(required=False, allow_blank=True)