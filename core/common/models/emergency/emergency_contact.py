"""
Emergency Contact models for ClustR application.
"""
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class EmergencyContactType(models.TextChoices):
    """Types of emergency contacts"""

    PERSONAL = "personal", _("Personal Contact")
    ESTATE_WIDE = "estate_wide", _("Estate-wide Contact")
    OFFICIAL = "official", _("Official Emergency Service")


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
        default_permissions = []
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

