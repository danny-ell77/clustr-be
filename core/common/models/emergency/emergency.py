"""
Emergency models for ClustR application.
"""

import logging
import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class EmergencyStatus(models.TextChoices):
    """Status of emergency alerts"""

    ACTIVE = "active", _("Active")
    ACKNOWLEDGED = "acknowledged", _("Acknowledged")
    RESPONDING = "responding", _("Responding")
    RESOLVED = "resolved", _("Resolved")
    CANCELLED = "cancelled", _("Cancelled")
    FALSE_ALARM = "false_alarm", _("False Alarm")


class EmergencyType(models.TextChoices):
    """Emergency types for categorization"""

    HEALTH = "health", _("Health Emergency")
    THEFT = "theft", _("Theft/Robbery")
    DOMESTIC_VIOLENCE = "domestic_violence", _("Domestic Violence")
    FIRE = "fire", _("Fire Emergency")
    SECURITY = "security", _("Security Issue")
    ACCIDENT = "accident", _("Accident")
    OTHER = "other", _("Other")


class SOSAlert(AbstractClusterModel):
    """
    Model for SOS emergency alerts.
    """

    alert_id = models.CharField(
        verbose_name=_("alert ID"),
        max_length=20,
        unique=True,
        help_text=_("Unique identifier for the alert"),
    )

    user = models.ForeignKey(
        verbose_name=_("user"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="sos_alerts",
        help_text=_("User who triggered the alert"),
    )

    emergency_type = models.CharField(
        verbose_name=_("emergency type"),
        max_length=20,
        choices=EmergencyType.choices,
        help_text=_("Type of emergency"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        help_text=_("Optional description of the emergency"),
    )

    location = models.CharField(
        verbose_name=_("location"),
        max_length=200,
        blank=True,
        help_text=_("Location of the emergency"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=EmergencyStatus.choices,
        default=EmergencyStatus.ACTIVE,
        help_text=_("Current status of the alert"),
    )

    priority = models.CharField(
        verbose_name=_("priority"),
        max_length=10,
        choices=[
            ("low", _("Low")),
            ("medium", _("Medium")),
            ("high", _("High")),
            ("critical", _("Critical")),
        ],
        default="high",
        help_text=_("Priority level of the alert"),
    )

    acknowledged_at = models.DateTimeField(
        verbose_name=_("acknowledged at"),
        null=True,
        blank=True,
        help_text=_("When the alert was acknowledged"),
    )

    acknowledged_by = models.ForeignKey(
        verbose_name=_("acknowledged by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="acknowledged_alerts",
        null=True,
        blank=True,
        help_text=_("User who acknowledged the alert"),
    )

    responded_at = models.DateTimeField(
        verbose_name=_("responded at"),
        null=True,
        blank=True,
        help_text=_("When response began"),
    )

    responded_by = models.ForeignKey(
        verbose_name=_("responded by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="responded_alerts",
        null=True,
        blank=True,
        help_text=_("User who responded to the alert"),
    )

    resolved_at = models.DateTimeField(
        verbose_name=_("resolved at"),
        null=True,
        blank=True,
        help_text=_("When the alert was resolved"),
    )

    resolved_by = models.ForeignKey(
        verbose_name=_("resolved by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="resolved_alerts",
        null=True,
        blank=True,
        help_text=_("User who resolved the alert"),
    )

    resolution_notes = models.TextField(
        verbose_name=_("resolution notes"),
        blank=True,
        help_text=_("Notes about the resolution"),
    )

    cancelled_at = models.DateTimeField(
        verbose_name=_("cancelled at"),
        null=True,
        blank=True,
        help_text=_("When the alert was cancelled"),
    )

    cancelled_by = models.ForeignKey(
        verbose_name=_("cancelled by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="cancelled_alerts",
        null=True,
        blank=True,
        help_text=_("User who cancelled the alert"),
    )

    cancellation_reason = models.TextField(
        verbose_name=_("cancellation reason"),
        blank=True,
        help_text=_("Reason for cancellation"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("SOS Alert")
        verbose_name_plural = _("SOS Alerts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "user"]),
            models.Index(fields=["cluster", "emergency_type"]),
            models.Index(fields=["cluster", "created_at"]),
        ]

    def __str__(self):
        return f"SOS Alert {self.alert_id} - {self.get_emergency_type_display()}"

    def save(self, *args, **kwargs):
        """Generate alert ID if not provided"""
        if not self.alert_id:
            import uuid

            self.alert_id = f"SOS-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def response_time_minutes(self):
        """Calculate response time in minutes"""
        if self.responded_at and self.created_at:
            return int((self.responded_at - self.created_at).total_seconds() / 60)
        return None

    @property
    def resolution_time_minutes(self):
        """Calculate resolution time in minutes"""
        if self.resolved_at and self.created_at:
            return int((self.resolved_at - self.created_at).total_seconds() / 60)
        return None

    @property
    def is_active(self):
        """Check if alert is still active"""
        return self.status in [
            EmergencyStatus.ACTIVE,
            EmergencyStatus.ACKNOWLEDGED,
            EmergencyStatus.RESPONDING,
        ]

    def acknowledge(self, user):
        """Acknowledge the alert"""
        from django.utils import timezone

        if self.status == EmergencyStatus.ACTIVE:
            self.status = EmergencyStatus.ACKNOWLEDGED
            self.acknowledged_at = timezone.now()
            self.acknowledged_by = user
            self.save(udpate_fields=["acknowledged_at", "acknowledged_by"])

    def start_response(self, user):
        """Mark response as started"""
        from django.utils import timezone

        if self.status in [EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED]:
            self.status = EmergencyStatus.RESPONDING
            self.responded_at = timezone.now()
            self.responded_by = user
            self.save(update_fields=["responded_at", "responded_by"])

    def resolve(self, user, notes=""):
        """Resolve the alert"""
        from django.utils import timezone

        if self.is_active:
            self.status = EmergencyStatus.RESOLVED
            self.resolved_at = timezone.now()
            self.resolved_by = user
            self.resolution_notes = notes
            self.save(update_fields=["resolved_by", "resolution_notes"])

    def cancel(self, user, reason=""):
        """Cancel the alert"""
        from django.utils import timezone

        if self.is_active:
            self.status = EmergencyStatus.CANCELLED
            self.cancelled_at = timezone.now()
            self.cancelled_by = user
            self.cancellation_reason = reason
            self.save(update_fields=["cancelled_by", "cancellation_reason"])

