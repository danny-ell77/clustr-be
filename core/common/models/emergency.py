"""
Emergency management models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from core.common.models.base import AbstractClusterModel


class EmergencyType(models.TextChoices):
    """Emergency types for categorization"""

    HEALTH = "health", _("Health Emergency")
    THEFT = "theft", _("Theft/Robbery")
    DOMESTIC_VIOLENCE = "domestic_violence", _("Domestic Violence")
    FIRE = "fire", _("Fire Emergency")
    SECURITY = "security", _("Security Issue")
    ACCIDENT = "accident", _("Accident")
    OTHER = "other", _("Other")


class EmergencyContactType(models.TextChoices):
    """Types of emergency contacts"""

    PERSONAL = "personal", _("Personal Contact")
    ESTATE_WIDE = "estate_wide", _("Estate-wide Contact")
    OFFICIAL = "official", _("Official Emergency Service")


class EmergencyStatus(models.TextChoices):
    """Status of emergency alerts"""

    ACTIVE = "active", _("Active")
    ACKNOWLEDGED = "acknowledged", _("Acknowledged")
    RESPONDING = "responding", _("Responding")
    RESOLVED = "resolved", _("Resolved")
    CANCELLED = "cancelled", _("Cancelled")
    FALSE_ALARM = "false_alarm", _("False Alarm")


class EmergencyContact(AbstractClusterModel):
    """
    Model for managing emergency contacts.
    Supports both personal and estate-wide emergency contacts.
    """

    name = models.CharField(
        verbose_name=_("contact name"),
        max_length=100,
        help_text=_("Name of the emergency contact"),
    )

    phone_number = models.CharField(
        verbose_name=_("phone number"),
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=_(
                    "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
                ),
            )
        ],
        help_text=_("Contact phone number"),
    )

    email = models.EmailField(
        verbose_name=_("email address"),
        blank=True,
        null=True,
        help_text=_("Contact email address (optional)"),
    )

    emergency_types = models.JSONField(
        verbose_name=_("emergency types"),
        default=list,
        help_text=_("List of emergency types this contact handles"),
    )

    contact_type = models.CharField(
        verbose_name=_("contact type"),
        max_length=20,
        choices=EmergencyContactType.choices,
        default=EmergencyContactType.PERSONAL,
        help_text=_("Type of emergency contact"),
    )

    user = models.ForeignKey(
        verbose_name=_("user"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
        null=True,
        blank=True,
        help_text=_("User who owns this contact (null for estate-wide contacts)"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether this contact is active and should receive alerts"),
    )

    is_primary = models.BooleanField(
        verbose_name=_("is primary"),
        default=False,
        help_text=_("Whether this is a primary contact for the emergency types"),
    )

    response_time_minutes = models.PositiveIntegerField(
        verbose_name=_("expected response time"),
        null=True,
        blank=True,
        help_text=_("Expected response time in minutes"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about this contact"),
    )

    class Meta:
        verbose_name = _("Emergency Contact")
        verbose_name_plural = _("Emergency Contacts")
        ordering = ["-is_primary", "name"]
        indexes = [
            models.Index(fields=["cluster", "contact_type"]),
            models.Index(fields=["cluster", "user"]),
            models.Index(fields=["cluster", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"

    def get_emergency_types_display(self):
        """Get display names for emergency types"""
        if not self.emergency_types:
            return []

        type_choices = dict(EmergencyType.choices)
        return [type_choices.get(et, et) for et in self.emergency_types]

    def handles_emergency_type(self, emergency_type):
        """Check if this contact handles a specific emergency type"""
        return emergency_type in self.emergency_types


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


class EmergencyResponse(AbstractClusterModel):
    """
    Model for tracking emergency response activities.
    """

    alert = models.ForeignKey(
        verbose_name=_("alert"),
        to="common.SOSAlert",
        on_delete=models.CASCADE,
        related_name="responses",
        help_text=_("The alert this response is for"),
    )

    responder = models.ForeignKey(
        verbose_name=_("responder"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="emergency_responses",
        help_text=_("User who responded"),
    )

    response_type = models.CharField(
        verbose_name=_("response type"),
        max_length=20,
        choices=[
            ("acknowledged", _("Acknowledged")),
            ("dispatched", _("Dispatched")),
            ("on_scene", _("On Scene")),
            ("resolved", _("Resolved")),
            ("cancelled", _("Cancelled")),
        ],
        help_text=_("Type of response"),
    )

    notes = models.TextField(
        verbose_name=_("notes"), blank=True, help_text=_("Response notes")
    )

    estimated_arrival = models.DateTimeField(
        verbose_name=_("estimated arrival"),
        null=True,
        blank=True,
        help_text=_("Estimated arrival time"),
    )

    actual_arrival = models.DateTimeField(
        verbose_name=_("actual arrival"),
        null=True,
        blank=True,
        help_text=_("Actual arrival time"),
    )

    class Meta:
        verbose_name = _("Emergency Response")
        verbose_name_plural = _("Emergency Responses")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "alert"]),
            models.Index(fields=["cluster", "responder"]),
        ]

    def __str__(self):
        return f"Response to {self.alert.alert_id} by {self.responder.name}"
