"""
Notification system models for ClustR.

This module contains models for logging and tracking notification attempts
across different channels and events.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import UUIDPrimaryKey, ObjectHistoryTracker


class NotificationLog(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    Audit log for all notification attempts.
    
    This model tracks every notification sent through the system for debugging,
    audit, and compliance purposes. It includes cluster scoping for multi-tenant
    data isolation.
    """
    
    cluster = models.ForeignKey(
        'common.Cluster',
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name=_("cluster"),
        help_text=_("The cluster this notification belongs to")
    )
    
    event = models.CharField(
        max_length=50,
        verbose_name=_("event"),
        help_text=_("Name of the notification event")
    )
    
    recipient = models.ForeignKey(
        'accounts.AccountUser',
        on_delete=models.CASCADE,
        related_name='received_notifications',
        verbose_name=_("recipient"),
        help_text=_("User who received the notification")
    )
    
    channel = models.CharField(
        max_length=20,
        default='EMAIL',
        verbose_name=_("channel"),
        help_text=_("Channel used to send the notification (EMAIL, SMS, etc.)")
    )
    
    success = models.BooleanField(
        default=False,
        verbose_name=_("success"),
        help_text=_("Whether the notification was sent successfully")
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("error message"),
        help_text=_("Error message if notification failed")
    )
    
    context_data = models.JSONField(
        default=dict,
        verbose_name=_("context data"),
        help_text=_("Context data used for the notification")
    )
    
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("sent at"),
        help_text=_("When the notification was sent")
    )
    
    class Meta:
        verbose_name = _("Notification Log")
        verbose_name_plural = _("Notification Logs")
        ordering = ['-sent_at']
        
        # Database indexes for efficient querying
        indexes = [
            models.Index(fields=['cluster', 'event'], name='notif_log_cluster_event_idx'),
            models.Index(fields=['cluster', 'recipient'], name='notif_log_cluster_recipient_idx'),
            models.Index(fields=['cluster', 'sent_at'], name='notif_log_cluster_sent_at_idx'),
            models.Index(fields=['event', 'sent_at'], name='notif_log_event_sent_at_idx'),
            models.Index(fields=['recipient', 'sent_at'], name='notif_log_recipient_sent_at_idx'),
            models.Index(fields=['success', 'sent_at'], name='notif_log_success_sent_at_idx'),
        ]
    
    def __str__(self):
        """String representation of the notification log."""
        status = "✓" if self.success else "✗"
        return f"{status} {self.event} → {self.recipient.email_address} via {self.channel}"
    
    @property
    def is_successful(self):
        """Check if notification was successful."""
        return self.success
    
    @property
    def has_error(self):
        """Check if notification had an error."""
        return not self.success and bool(self.error_message)
    
    def get_context_summary(self):
        """Get a summary of context data for display purposes."""
        if not self.context_data:
            return "No context data"
        
        # Show first few keys for summary
        keys = list(self.context_data.keys())[:3]
        if len(self.context_data) > 3:
            keys.append(f"... and {len(self.context_data) - 3} more")
        
        return f"Context: {', '.join(keys)}"