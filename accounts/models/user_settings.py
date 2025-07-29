"""
User settings models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models import UUIDPrimaryKey, ObjectHistoryTracker


class NotificationChannel(models.TextChoices):
    """Notification delivery channels"""
    EMAIL = "EMAIL", _("Email")
    SMS = "SMS", _("SMS")
    PUSH = "PUSH", _("Push Notification")
    IN_APP = "IN_APP", _("In-App Notification")


class NotificationType(models.TextChoices):
    """Types of notifications that can be configured"""
    VISITOR_ARRIVAL = "VISITOR_ARRIVAL", _("Visitor Arrival")
    VISITOR_OVERSTAY = "VISITOR_OVERSTAY", _("Visitor Overstay")
    ANNOUNCEMENT = "ANNOUNCEMENT", _("Announcements")
    COMMENT_REPLY = "COMMENT_REPLY", _("Comment Replies")
    ISSUE_STATUS_CHANGE = "ISSUE_STATUS_CHANGE", _("Issue Status Changes")
    ISSUE_COMMENT = "ISSUE_COMMENT", _("Issue Comments")
    ISSUE_ASSIGNMENT = "ISSUE_ASSIGNMENT", _("Issue Assignment")
    POLL_NOTIFICATION = "POLL_NOTIFICATION", _("Poll Notifications")
    EMERGENCY_ALERT = "EMERGENCY_ALERT", _("Emergency Alerts")
    PAYMENT_REMINDER = "PAYMENT_REMINDER", _("Payment Reminders")
    PAYMENT_CONFIRMATION = "PAYMENT_CONFIRMATION", _("Payment Confirmations")
    BILL_NOTIFICATION = "BILL_NOTIFICATION", _("Bill Notifications")
    CHILD_EXIT = "CHILD_EXIT", _("Child Exit Notifications")
    CHILD_ENTRY = "CHILD_ENTRY", _("Child Entry Notifications")
    CHILD_OVERDUE = "CHILD_OVERDUE", _("Child Overdue Notifications")
    EXIT_REQUEST = "EXIT_REQUEST", _("Exit Request Notifications")
    MARKETPLACE_ACTIVITY = "MARKETPLACE_ACTIVITY", _("Marketplace Activity")
    SHIFT_REMINDER = "SHIFT_REMINDER", _("Shift Reminders")
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT", _("Task Assignment")
    TASK_DUE = "TASK_DUE", _("Task Due Reminders")
    MAINTENANCE_ALERT = "MAINTENANCE_ALERT", _("Maintenance Alerts")


class SettingsCategory(models.TextChoices):
    """Categories for organizing user settings"""
    NOTIFICATIONS = "NOTIFICATIONS", _("Notifications")
    PRIVACY = "PRIVACY", _("Privacy")
    SECURITY = "SECURITY", _("Security")
    PREFERENCES = "PREFERENCES", _("Preferences")
    COMMUNICATION = "COMMUNICATION", _("Communication")


class UserSettings(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    User settings model for storing user preferences and configurations.
    """
    
    user = models.OneToOneField(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name=_("User")
    )
    
    # Notification preferences
    notification_preferences = models.JSONField(
        default=dict,
        verbose_name=_("Notification Preferences"),
        help_text=_("JSON object storing notification preferences by type and channel")
    )
    
    # Privacy settings
    privacy_settings = models.JSONField(
        default=dict,
        verbose_name=_("Privacy Settings"),
        help_text=_("JSON object storing privacy preferences")
    )
    
    # General preferences
    general_preferences = models.JSONField(
        default=dict,
        verbose_name=_("General Preferences"),
        help_text=_("JSON object storing general user preferences")
    )
    
    # Communication preferences
    communication_preferences = models.JSONField(
        default=dict,
        verbose_name=_("Communication Preferences"),
        help_text=_("JSON object storing communication preferences")
    )
    
    # Timezone preference
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        verbose_name=_("Timezone"),
        help_text=_("User's preferred timezone")
    )
    
    # Language preference
    language = models.CharField(
        max_length=10,
        default="en",
        verbose_name=_("Language"),
        help_text=_("User's preferred language")
    )
    
    # Theme preference
    theme = models.CharField(
        max_length=20,
        default="light",
        choices=[
            ("light", _("Light")),
            ("dark", _("Dark")),
            ("auto", _("Auto"))
        ],
        verbose_name=_("Theme"),
        help_text=_("User's preferred theme")
    )
    
    class Meta:
        verbose_name = _("User Settings")
        verbose_name_plural = _("User Settings")
        default_permissions = []
    
    def __str__(self):
        return f"Settings for {self.user.name}"
    
    def get_notification_preference(self, notification_type: str, channel: str) -> bool:
        """
        Get notification preference for a specific type and channel.
        
        Args:
            notification_type: Type of notification
            channel: Notification channel
            
        Returns:
            Boolean indicating if notifications are enabled for this type/channel
        """
        return self.notification_preferences.get(notification_type, {}).get(channel, True)
    
    def set_notification_preference(self, notification_type: str, channel: str, enabled: bool):
        """
        Set notification preference for a specific type and channel.
        
        Args:
            notification_type: Type of notification
            channel: Notification channel
            enabled: Whether to enable notifications for this type/channel
        """
        if notification_type not in self.notification_preferences:
            self.notification_preferences[notification_type] = {}
        
        self.notification_preferences[notification_type][channel] = enabled
        self.save(update_fields=['notification_preferences'])
    
    def get_privacy_setting(self, setting_key: str, default=None):
        """
        Get a privacy setting value.
        
        Args:
            setting_key: The privacy setting key
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value or default
        """
        return self.privacy_settings.get(setting_key, default)
    
    def set_privacy_setting(self, setting_key: str, value):
        """
        Set a privacy setting value.
        
        Args:
            setting_key: The privacy setting key
            value: The value to set
        """
        self.privacy_settings[setting_key] = value
        self.save(update_fields=['privacy_settings'])
    
    def get_general_preference(self, preference_key: str, default=None):
        """
        Get a general preference value.
        
        Args:
            preference_key: The preference key
            default: Default value if preference doesn't exist
            
        Returns:
            The preference value or default
        """
        return self.general_preferences.get(preference_key, default)
    
    def set_general_preference(self, preference_key: str, value):
        """
        Set a general preference value.
        
        Args:
            preference_key: The preference key
            value: The value to set
        """
        self.general_preferences[preference_key] = value
        self.save(update_fields=['general_preferences'])
    
    @classmethod
    def get_default_notification_preferences(cls):
        """
        Get default notification preferences for new users.
        
        Returns:
            Dictionary with default notification preferences
        """
        defaults = {}
        
        # Enable all notification types for email by default
        for notification_type in NotificationType.values:
            defaults[notification_type] = {
                NotificationChannel.EMAIL: True,
                NotificationChannel.SMS: False,  # SMS disabled by default due to cost
                NotificationChannel.PUSH: True,
                NotificationChannel.IN_APP: True,
            }
        
        # Override specific defaults
        # Emergency alerts should be enabled for all channels
        defaults[NotificationType.EMERGENCY_ALERT] = {
            NotificationChannel.EMAIL: True,
            NotificationChannel.SMS: True,
            NotificationChannel.PUSH: True,
            NotificationChannel.IN_APP: True,
        }
        
        # Child-related notifications should be enabled for all channels for parents
        child_notifications = [
            NotificationType.CHILD_EXIT,
            NotificationType.CHILD_ENTRY,
            NotificationType.CHILD_OVERDUE,
            NotificationType.EXIT_REQUEST,
        ]
        
        for notification_type in child_notifications:
            defaults[notification_type] = {
                NotificationChannel.EMAIL: True,
                NotificationChannel.SMS: True,
                NotificationChannel.PUSH: True,
                NotificationChannel.IN_APP: True,
            }
        
        return defaults
    
    @classmethod
    def get_default_privacy_settings(cls):
        """
        Get default privacy settings for new users.
        
        Returns:
            Dictionary with default privacy settings
        """
        return {
            'profile_visibility': 'cluster_members',  # visible to cluster members only
            'contact_info_visibility': 'cluster_admins',  # contact info visible to admins only
            'activity_visibility': 'private',  # activity private by default
            'marketplace_profile_public': False,  # marketplace profile private by default
            'allow_direct_messages': True,  # allow direct messages from cluster members
            'show_online_status': True,  # show online status to cluster members
        }
    
    @classmethod
    def get_default_general_preferences(cls):
        """
        Get default general preferences for new users.
        
        Returns:
            Dictionary with default general preferences
        """
        return {
            'dashboard_layout': 'default',
            'items_per_page': 20,
            'auto_refresh_dashboard': True,
            'show_welcome_messages': True,
            'compact_view': False,
        }
    
    def save(self, *args, **kwargs):
        """Override save to set defaults for new instances."""
        if not self.pk:
            # Set defaults for new instances
            if not self.notification_preferences:
                self.notification_preferences = self.get_default_notification_preferences()
            if not self.privacy_settings:
                self.privacy_settings = self.get_default_privacy_settings()
            if not self.general_preferences:
                self.general_preferences = self.get_default_general_preferences()
        
        super().save(*args, **kwargs)


class NotificationPreference(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    Individual notification preference model for more granular control.
    This provides a normalized alternative to the JSON field approach.
    """
    
    user = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="notification_preferences_detailed",
        verbose_name=_("User")
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        verbose_name=_("Notification Type")
    )
    
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        verbose_name=_("Channel")
    )
    
    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled"),
        help_text=_("Whether this notification type is enabled for this channel")
    )
    
    # Optional cluster-specific preferences
    cluster = models.ForeignKey(
        "common.Cluster",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_preferences",
        verbose_name=_("Cluster"),
        help_text=_("Cluster-specific notification preference (optional)")
    )
    
    class Meta:
        verbose_name = _("Notification Preference")
        verbose_name_plural = _("Notification Preferences")
        unique_together = [
            ('user', 'notification_type', 'channel', 'cluster')
        ]
        indexes = [
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['user', 'channel']),
            models.Index(fields=['cluster', 'notification_type']),
        ]
        default_permissions = []
    
    def __str__(self):
        cluster_info = f" ({self.cluster.name})" if self.cluster else ""
        return f"{self.user.name} - {self.get_notification_type_display()} via {self.get_channel_display()}{cluster_info}: {'Enabled' if self.enabled else 'Disabled'}"