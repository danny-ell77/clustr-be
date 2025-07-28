"""
Serializers for user settings functionality.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from accounts.models import UserSettings, NotificationPreference, NotificationChannel, NotificationType


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for individual notification preferences."""
    
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    channel_display = serializers.CharField(
        source='get_channel_display',
        read_only=True
    )
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'channel',
            'channel_display',
            'enabled',
            'cluster',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationPreferencesUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating notification preferences."""
    
    preferences = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        help_text=_("List of preference objects with notification_type, channel, and enabled fields")
    )
    
    def validate_preferences(self, value):
        """Validate the preferences list."""
        for pref in value:
            # Check required fields
            if not all(key in pref for key in ['notification_type', 'channel', 'enabled']):
                raise serializers.ValidationError(
                    _("Each preference must have notification_type, channel, and enabled fields")
                )
            
            # Validate notification_type
            if pref['notification_type'] not in [choice[0] for choice in NotificationType.choices]:
                raise serializers.ValidationError(
                    _("Invalid notification_type: {type}").format(type=pref['notification_type'])
                )
            
            # Validate channel
            if pref['channel'] not in [choice[0] for choice in NotificationChannel.choices]:
                raise serializers.ValidationError(
                    _("Invalid channel: {channel}").format(channel=pref['channel'])
                )
            
            # Validate enabled
            if not isinstance(pref['enabled'], bool):
                raise serializers.ValidationError(
                    _("enabled field must be a boolean")
                )
        
        return value


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user settings."""
    
    notification_preferences_detailed = NotificationPreferenceSerializer(
        many=True,
        read_only=True
    )
    
    class Meta:
        model = UserSettings
        fields = [
            'id',
            'notification_preferences',
            'privacy_settings',
            'general_preferences',
            'communication_preferences',
            'timezone',
            'language',
            'theme',
            'notification_preferences_detailed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_timezone(self, value):
        """Validate timezone value."""
        import pytz
        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError(_("Invalid timezone"))
        return value
    
    def validate_language(self, value):
        """Validate language code."""
        from django.conf import settings
        
        # Get available languages from Django settings
        available_languages = [lang[0] for lang in getattr(settings, 'LANGUAGES', [('en', 'English')])]
        
        if value not in available_languages:
            raise serializers.ValidationError(
                _("Language must be one of: {languages}").format(
                    languages=', '.join(available_languages)
                )
            )
        return value


class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    """Serializer for updating a single notification preference."""
    
    notification_type = serializers.ChoiceField(
        choices=NotificationType.choices,
        help_text=_("Type of notification")
    )
    
    channel = serializers.ChoiceField(
        choices=NotificationChannel.choices,
        help_text=_("Notification channel")
    )
    
    enabled = serializers.BooleanField(
        help_text=_("Whether to enable this notification")
    )


class PrivacySettingsUpdateSerializer(serializers.Serializer):
    """Serializer for updating privacy settings."""
    
    profile_visibility = serializers.ChoiceField(
        choices=[
            ('public', _('Public')),
            ('cluster_members', _('Cluster Members')),
            ('private', _('Private')),
        ],
        required=False,
        help_text=_("Who can view your profile")
    )
    
    contact_info_visibility = serializers.ChoiceField(
        choices=[
            ('public', _('Public')),
            ('cluster_members', _('Cluster Members')),
            ('cluster_admins', _('Cluster Admins Only')),
            ('private', _('Private')),
        ],
        required=False,
        help_text=_("Who can view your contact information")
    )
    
    activity_visibility = serializers.ChoiceField(
        choices=[
            ('public', _('Public')),
            ('cluster_members', _('Cluster Members')),
            ('private', _('Private')),
        ],
        required=False,
        help_text=_("Who can view your activity")
    )
    
    marketplace_profile_public = serializers.BooleanField(
        required=False,
        help_text=_("Make your marketplace profile public")
    )
    
    allow_direct_messages = serializers.BooleanField(
        required=False,
        help_text=_("Allow direct messages from other users")
    )
    
    show_online_status = serializers.BooleanField(
        required=False,
        help_text=_("Show your online status to other users")
    )


class GeneralPreferencesUpdateSerializer(serializers.Serializer):
    """Serializer for updating general preferences."""
    
    dashboard_layout = serializers.ChoiceField(
        choices=[
            ('default', _('Default')),
            ('compact', _('Compact')),
            ('expanded', _('Expanded')),
        ],
        required=False,
        help_text=_("Dashboard layout preference")
    )
    
    items_per_page = serializers.IntegerField(
        min_value=10,
        max_value=100,
        required=False,
        help_text=_("Number of items to display per page")
    )
    
    auto_refresh_dashboard = serializers.BooleanField(
        required=False,
        help_text=_("Automatically refresh dashboard data")
    )
    
    show_welcome_messages = serializers.BooleanField(
        required=False,
        help_text=_("Show welcome messages and tips")
    )
    
    compact_view = serializers.BooleanField(
        required=False,
        help_text=_("Use compact view for lists and tables")
    )


class CommunicationPreferencesUpdateSerializer(serializers.Serializer):
    """Serializer for updating communication preferences."""
    
    preferred_contact_method = serializers.ChoiceField(
        choices=[
            ('email', _('Email')),
            ('sms', _('SMS')),
            ('phone', _('Phone')),
            ('in_app', _('In-App')),
        ],
        required=False,
        help_text=_("Preferred method for important communications")
    )
    
    auto_reply_enabled = serializers.BooleanField(
        required=False,
        help_text=_("Enable auto-reply for messages")
    )
    
    auto_reply_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text=_("Auto-reply message content")
    )
    
    message_preview_enabled = serializers.BooleanField(
        required=False,
        help_text=_("Show message previews in notifications")
    )


class UserSettingsUpdateSerializer(serializers.Serializer):
    """Serializer for updating user settings."""
    
    timezone = serializers.CharField(
        max_length=50,
        required=False,
        help_text=_("User's preferred timezone")
    )
    
    language = serializers.CharField(
        max_length=10,
        required=False,
        help_text=_("User's preferred language")
    )
    
    theme = serializers.ChoiceField(
        choices=[
            ('light', _('Light')),
            ('dark', _('Dark')),
            ('auto', _('Auto')),
        ],
        required=False,
        help_text=_("User's preferred theme")
    )
    
    notification_preferences = NotificationPreferencesUpdateSerializer(required=False)
    privacy_settings = PrivacySettingsUpdateSerializer(required=False)
    general_preferences = GeneralPreferencesUpdateSerializer(required=False)
    communication_preferences = CommunicationPreferencesUpdateSerializer(required=False)
    
    def validate_timezone(self, value):
        """Validate timezone value."""
        import pytz
        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError(_("Invalid timezone"))
        return value
    
    def validate_language(self, value):
        """Validate language code."""
        from django.conf import settings
        
        # Get available languages from Django settings
        available_languages = [lang[0] for lang in getattr(settings, 'LANGUAGES', [('en', 'English')])]
        
        if value not in available_languages:
            raise serializers.ValidationError(
                _("Language must be one of: {languages}").format(
                    languages=', '.join(available_languages)
                )
            )
        return value