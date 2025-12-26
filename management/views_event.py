"""
Views for event management in the management app.
"""

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from management.filters import EventFilter, EventGuestFilter

from accounts.permissions import HasClusterPermission
from core.common.models import Event, EventGuest
from core.common.permissions import AccessControlPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.event_serializers import (
    EventSerializer,
    EventCreateSerializer,
    EventUpdateSerializer,
    EventGuestSerializer,
    EventGuestCreateSerializer,
    BulkGuestCreateSerializer,
    EventGuestCheckInSerializer,
    EventGuestCheckOutSerializer,
)


@audit_viewset(resource_type='event')
class ManagementEventViewSet(ModelViewSet):
    """
    ViewSet for managing events in the management app.
    Allows administrators to view and manage all events in the estate.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageEvent]),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventFilter
    
    def get_queryset(self):
        """
        Return all events for the current cluster.
        """
        return Event.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        elif self.action == 'add_guests':
            return BulkGuestCreateSerializer
        return EventSerializer
    
    def perform_create(self, serializer):
        """
        Create a new event and set the created_by field to the current user.
        """
        serializer.save(created_by=self.request.user.id)
    
    @action(detail=True, methods=['post'])
    def add_guests(self, request, pk=None):
        """
        Add multiple guests to an event at once.
        """
        event = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            guests_data = serializer.validated_data['guests']
            created_guests = []
            
            for guest_data in guests_data:
                guest_serializer = EventGuestCreateSerializer(data=guest_data)
                if guest_serializer.is_valid():
                    guest = guest_serializer.save(
                        event=event,
                        invited_by=request.user.id,
                        cluster=event.cluster
                    )
                    created_guests.append(guest)
                else:
                    # If any guest data is invalid, return the errors
                    return Response(
                        guest_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Update the guests_added count
            event.guests_added = event.guests.count()
            event.save()
            
            return Response(
                EventGuestSerializer(created_guests, many=True).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish an event.
        """
        event = self.get_object()
        
        if event.status == Event.Status.DRAFT:
            event.status = Event.Status.PUBLISHED
            event.save()
            
            return Response(
                EventSerializer(event).data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'Only draft events can be published'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel an event.
        """
        event = self.get_object()
        
        if event.status in [Event.Status.DRAFT, Event.Status.PUBLISHED]:
            event.status = Event.Status.CANCELLED
            event.save()
            
            return Response(
                EventSerializer(event).data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'Only draft or published events can be cancelled'},
            status=status.HTTP_400_BAD_REQUEST
        )


@audit_viewset(resource_type='event_guest')
class ManagementEventGuestViewSet(ModelViewSet):
    """
    ViewSet for managing event guests in the management app.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageEvent]),
    ]
    
    def get_queryset(self):
        """
        Return all event guests for the current cluster.
        """
        if getattr(self, "swagger_fake_view", False):
            return EventGuest.objects.none()

        event_id = self.kwargs.get('event_pk')
        if event_id:
            return EventGuest.objects.filter(event_id=event_id)
        return EventGuest.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return EventGuestCreateSerializer
        elif self.action == 'check_in':
            return EventGuestCheckInSerializer
        elif self.action == 'check_out':
            return EventGuestCheckOutSerializer
        return EventGuestSerializer
    
    def perform_create(self, serializer):
        """
        Create a new event guest and set the invited_by field to the current user.
        """
        event_id = self.kwargs.get('event_pk')
        event = Event.objects.get(id=event_id)
        
        serializer.save(
            event=event,
            invited_by=self.request.user.id,
            cluster=event.cluster
        )
        
        # Update the guests_added count
        event.guests_added = event.guests.count()
        event.save()
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None, event_pk=None):
        """
        Check in an event guest.
        """
        guest = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            guest.status = EventGuest.Status.ATTENDED
            guest.check_in_time = timezone.now()
            if 'notes' in serializer.validated_data:
                guest.notes = serializer.validated_data['notes']
            guest.save()
            
            return Response(
                EventGuestSerializer(guest).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None, event_pk=None):
        """
        Check out an event guest.
        """
        guest = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            guest.check_out_time = timezone.now()
            if 'notes' in serializer.validated_data:
                guest.notes = (guest.notes or '') + '\n' + serializer.validated_data['notes']
            guest.save()
            
            return Response(
                EventGuestSerializer(guest).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)