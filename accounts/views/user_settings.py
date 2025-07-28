"""
Views for user settings management.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from accounts.models import UserSettings, NotificationPreference
from accounts.serializers import (
    UserSettingsSerializer,
    UserSettingsUpdateSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
    NotificationPreferencesUpdateSerializer,
    PrivacySettingsUpdateSerializer,
    GeneralPreferencesUpdateSerializer,
    CommunicationPreferencesUpdateSerializer,
)
from core.common.permissions import IsOwnerOrReadOnly


class UserSettingsViewSet(ModelViewSet):
    """
    ViewSet for managing user settings.
    """
    
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """Return settings for the current user only."""
        return UserSettings.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create user settings for the current user."""
        settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings
    
    def list(self, request, *args, **kwargs):
        """Return the current user's settings."""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Not allowed - settings are auto-created."""
        return Response(
            {'error': _('Settings are automatically created for each user')},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        """Update user settings."""
        settings = self.get_object()
        serializer = UserSettingsUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                # Update basic settings
                for field in ['timezone', 'language', 'theme']:
                    if field in serializer.validated_data:
                        setattr(settings, field, serializer.validated_data[field])
                
                # Update notification preferences
                if 'notification_preferences' in serializer.validated_data:
                    self._update_notification_preferences(
                        settings, 
                        serializer.validated_data['notification_preferences']
                    )
                
                # Update privacy settings
                if 'privacy_settings' in serializer.validated_data:
                    self._update_privacy_settings(
                        settings,
                        serializer.validated_data['privacy_settings']
                    )
                
                # Update general preferences
                if 'general_preferences' in serializer.validated_data:
                    self._update_general_preferences(
                        settings,
                        serializer.validated_data['general_preferences']
                    )
                
                # Update communication preferences
                if 'communication_preferences' in serializer.validated_data:
                    self._update_communication_preferences(
                        settings,
                        serializer.validated_data['communication_preferences']
                    )
                
                settings.save()
            
            # Return updated settings
            response_serializer = UserSettingsSerializer(settings)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_notification_preferences(self, settings, preferences_data):
        """Update notification preferences."""
        if 'preferences' in preferences_data:
            for pref in preferences_data['preferences']:
                settings.set_notification_preference(
                    pref['notification_type'],
                    pref['channel'],
                    pref['enabled']
                )
    
    def _update_privacy_settings(self, settings, privacy_data):
        """Update privacy settings."""
        for key, value in privacy_data.items():
            settings.set_privacy_setting(key, value)
    
    def _update_general_preferences(self, settings, preferences_data):
        """Update general preferences."""
        for key, value in preferences_data.items():
            settings.set_general_preference(key, value)
    
    def _update_communication_preferences(self, settings, comm_data):
        """Update communication preferences."""
        current_prefs = settings.communication_preferences
        current_prefs.update(comm_data)
        settings.communication_preferences = current_prefs
    
    @action(detail=False, methods=['get'])
    def notification_preferences(self, request):
        """Get current notification preferences."""
        settings = self.get_object()
        return Response({
            'notification_preferences': settings.notification_preferences,
            'available_types': [
                {'value': choice[0], 'label': choice[1]} 
                for choice in NotificationPreference._meta.get_field('notification_type').choices
            ],
            'available_channels': [
                {'value': choice[0], 'label': choice[1]} 
                for choice in NotificationPreference._meta.get_field('channel').choices
            ]
        })
    
    @action(detail=False, methods=['post'])
    def update_notification_preference(self, request):
        """Update a single notification preference."""
        serializer = NotificationPreferenceUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            settings = self.get_object()
            settings.set_notification_preference(
                serializer.validated_data['notification_type'],
                serializer.validated_data['channel'],
                serializer.validated_data['enabled']
            )
            
            return Response({
                'message': _('Notification preference updated successfully'),
                'preference': {
                    'notification_type': serializer.validated_data['notification_type'],
                    'channel': serializer.validated_data['channel'],
                    'enabled': serializer.validated_data['enabled'],
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_update_notification_preferences(self, request):
        """Bulk update notification preferences."""
        serializer = NotificationPreferencesUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            settings = self.get_object()
            
            with transaction.atomic():
                for pref in serializer.validated_data['preferences']:
                    settings.set_notification_preference(
                        pref['notification_type'],
                        pref['channel'],
                        pref['enabled']
                    )
            
            return Response({
                'message': _('Notification preferences updated successfully'),
                'updated_count': len(serializer.validated_data['preferences'])
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def privacy_settings(self, request):
        """Get current privacy settings."""
        settings = self.get_object()
        return Response({
            'privacy_settings': settings.privacy_settings,
            'available_options': {
                'profile_visibility': [
                    {'value': 'public', 'label': _('Public')},
                    {'value': 'cluster_members', 'label': _('Cluster Members')},
                    {'value': 'private', 'label': _('Private')},
                ],
                'contact_info_visibility': [
                    {'value': 'public', 'label': _('Public')},
                    {'value': 'cluster_members', 'label': _('Cluster Members')},
                    {'value': 'cluster_admins', 'label': _('Cluster Admins Only')},
                    {'value': 'private', 'label': _('Private')},
                ],
                'activity_visibility': [
                    {'value': 'public', 'label': _('Public')},
                    {'value': 'cluster_members', 'label': _('Cluster Members')},
                    {'value': 'private', 'label': _('Private')},
                ],
            }
        })
    
    @action(detail=False, methods=['post'])
    def update_privacy_settings(self, request):
        """Update privacy settings."""
        serializer = PrivacySettingsUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            settings = self.get_object()
            
            for key, value in serializer.validated_data.items():
                settings.set_privacy_setting(key, value)
            
            return Response({
                'message': _('Privacy settings updated successfully'),
                'privacy_settings': settings.privacy_settings
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def general_preferences(self, request):
        """Get current general preferences."""
        settings = self.get_object()
        return Response({
            'general_preferences': settings.general_preferences,
            'available_options': {
                'dashboard_layout': [
                    {'value': 'default', 'label': _('Default')},
                    {'value': 'compact', 'label': _('Compact')},
                    {'value': 'expanded', 'label': _('Expanded')},
                ],
                'theme': [
                    {'value': 'light', 'label': _('Light')},
                    {'value': 'dark', 'label': _('Dark')},
                    {'value': 'auto', 'label': _('Auto')},
                ],
            }
        })
    
    @action(detail=False, methods=['post'])
    def update_general_preferences(self, request):
        """Update general preferences."""
        serializer = GeneralPreferencesUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            settings = self.get_object()
            
            for key, value in serializer.validated_data.items():
                settings.set_general_preference(key, value)
            
            return Response({
                'message': _('General preferences updated successfully'),
                'general_preferences': settings.general_preferences
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def communication_preferences(self, request):
        """Get current communication preferences."""
        settings = self.get_object()
        return Response({
            'communication_preferences': settings.communication_preferences,
            'available_options': {
                'preferred_contact_method': [
                    {'value': 'email', 'label': _('Email')},
                    {'value': 'sms', 'label': _('SMS')},
                    {'value': 'phone', 'label': _('Phone')},
                    {'value': 'in_app', 'label': _('In-App')},
                ],
            }
        })
    
    @action(detail=False, methods=['post'])
    def update_communication_preferences(self, request):
        """Update communication preferences."""
        serializer = CommunicationPreferencesUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            settings = self.get_object()
            
            current_prefs = settings.communication_preferences
            current_prefs.update(serializer.validated_data)
            settings.communication_preferences = current_prefs
            settings.save(update_fields=['communication_preferences'])
            
            return Response({
                'message': _('Communication preferences updated successfully'),
                'communication_preferences': settings.communication_preferences
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reset_to_defaults(self, request):
        """Reset settings to default values."""
        settings = self.get_object()
        
        with transaction.atomic():
            settings.notification_preferences = settings.get_default_notification_preferences()
            settings.privacy_settings = settings.get_default_privacy_settings()
            settings.general_preferences = settings.get_default_general_preferences()
            settings.communication_preferences = {}
            settings.timezone = "UTC"
            settings.language = "en"
            settings.theme = "light"
            settings.save()
        
        serializer = UserSettingsSerializer(settings)
        return Response({
            'message': _('Settings reset to defaults successfully'),
            'settings': serializer.data
        })


class NotificationPreferenceViewSet(ModelViewSet):
    """
    ViewSet for managing individual notification preferences.
    """
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return notification preferences for the current user only."""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set the user to the current user when creating."""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Ensure user cannot be changed when updating."""
        serializer.save(user=self.request.user)