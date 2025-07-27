from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models import UUIDPrimaryKey, ObjectHistoryTracker


class EmergencyContactType(models.TextChoices):
    """Types of emergency contacts"""
    HEALTH = "HEALTH", _("Health Emergency")
    SECURITY = "SECURITY", _("Security Emergency")
    FIRE = "FIRE", _("Fire Emergency")
    DOMESTIC = "DOMESTIC", _("Domestic Violence")
    OTHER = "OTHER", _("Other Emergency")


class EmergencyContact(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    Emergency contacts for users.
    These contacts will be notified in case of emergencies.
    """
    user = models.ForeignKey(
        verbose_name=_("user"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
        related_query_name="emergency_contact",
        help_text=_("The user this emergency contact belongs to"),
    )
    name = models.CharField(
        verbose_name=_("contact name"),
        max_length=255,
        help_text=_("Name of the emergency contact"),
    )
    relationship = models.CharField(
        verbose_name=_("relationship"),
        max_length=100,
        help_text=_("Relationship to the user (e.g., spouse, parent, friend)"),
    )
    phone_number = models.CharField(
        verbose_name=_("phone number"),
        max_length=16,
        help_text=_("Phone number of the emergency contact in E.164 format"),
    )
    email = models.EmailField(
        verbose_name=_("email address"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Email address of the emergency contact"),
    )
    contact_type = models.CharField(
        verbose_name=_("contact type"),
        max_length=20,
        choices=EmergencyContactType.choices,
        default=EmergencyContactType.OTHER,
        help_text=_("Type of emergency this contact should be notified for"),
    )
    is_primary = models.BooleanField(
        verbose_name=_("is primary contact"),
        default=False,
        help_text=_("Whether this is the primary emergency contact"),
    )
    
    class Meta:
        verbose_name = _("emergency contact")
        verbose_name_plural = _("emergency contacts")
        ordering = ["-is_primary", "name"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["contact_type"]),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()}) - {self.user.name}"