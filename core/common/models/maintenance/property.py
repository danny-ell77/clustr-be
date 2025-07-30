"""
Property models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class PropertyType(models.TextChoices):
    """Types of properties that can be maintained."""

    BUILDING = "BUILDING", _("Building")
    ELECTRICAL = "ELECTRICAL", _("Electrical")
    PLUMBING = "PLUMBING", _("Plumbing")
    HVAC = "HVAC", _("HVAC")
    SECURITY = "SECURITY", _("Security")
    LANDSCAPING = "LANDSCAPING", _("Landscaping")
    EQUIPMENT = "EQUIPMENT", _("Equipment")
    INFRASTRUCTURE = "INFRASTRUCTURE", _("Infrastructure")
    OTHER = "OTHER", _("Other")


class MaintenanceSchedule(AbstractClusterModel):
    """
    Model for scheduling preventive maintenance.
    """

    name = models.CharField(
        verbose_name=_("schedule name"),
        max_length=200,
        help_text=_("Name of the maintenance schedule"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Description of the scheduled maintenance"),
    )

    property_type = models.CharField(
        verbose_name=_("property type"),
        max_length=20,
        choices=PropertyType.choices,
        help_text=_("Type of property or equipment"),
    )

    property_location = models.CharField(
        verbose_name=_("property location"),
        max_length=200,
        help_text=_("Specific location of the property or equipment"),
    )

    equipment_name = models.CharField(
        verbose_name=_("equipment name"),
        max_length=200,
        blank=True,
        help_text=_("Name or model of the equipment (if applicable)"),
    )

    frequency_type = models.CharField(
        verbose_name=_("frequency type"),
        max_length=20,
        choices=[
            ("DAILY", _("Daily")),
            ("WEEKLY", _("Weekly")),
            ("MONTHLY", _("Monthly")),
            ("QUARTERLY", _("Quarterly")),
            ("SEMI_ANNUAL", _("Semi-Annual")),
            ("ANNUAL", _("Annual")),
            ("CUSTOM", _("Custom")),
        ],
        default="MONTHLY",
        help_text=_("How often the maintenance should be performed"),
    )

    frequency_value = models.PositiveIntegerField(
        verbose_name=_("frequency value"),
        default=1,
        help_text=_("Numeric value for custom frequency (e.g., every 3 months)"),
    )

    next_due_date = models.DateTimeField(
        verbose_name=_("next due date"), help_text=_("When the next maintenance is due")
    )

    estimated_duration = models.DurationField(
        verbose_name=_("estimated duration"),
        null=True,
        blank=True,
        help_text=_("Estimated time to complete the maintenance"),
    )

    estimated_cost = models.DecimalField(
        verbose_name=_("estimated cost"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Estimated cost of the maintenance"),
    )

    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_maintenance_schedules",
        help_text=_("Staff member assigned to this maintenance"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether this schedule is active"),
    )

    instructions = models.TextField(
        verbose_name=_("instructions"),
        blank=True,
        help_text=_("Instructions for performing the maintenance"),
    )

    materials_needed = models.TextField(
        verbose_name=_("materials needed"),
        blank=True,
        help_text=_("List of materials typically needed"),
    )

    tools_needed = models.TextField(
        verbose_name=_("tools needed"),
        blank=True,
        help_text=_("List of tools typically needed"),
    )

    class Meta:
        verbose_name = _("maintenance schedule")
        verbose_name_plural = _("maintenance schedules")
        ordering = ["next_due_date"]
        indexes = [
            models.Index(fields=["next_due_date"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["property_type"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.property_location}"

    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency."""
        if self.frequency_type == "DAILY":
            return self.next_due_date + timedelta(days=self.frequency_value)
        elif self.frequency_type == "WEEKLY":
            return self.next_due_date + timedelta(weeks=self.frequency_value)
        elif self.frequency_type == "MONTHLY":
            # Approximate monthly calculation
            return self.next_due_date + timedelta(days=30 * self.frequency_value)
        elif self.frequency_type == "QUARTERLY":
            return self.next_due_date + timedelta(days=90 * self.frequency_value)
        elif self.frequency_type == "SEMI_ANNUAL":
            return self.next_due_date + timedelta(days=180 * self.frequency_value)
        elif self.frequency_type == "ANNUAL":
            return self.next_due_date + timedelta(days=365 * self.frequency_value)
        else:
            # Custom frequency - default to monthly
            return self.next_due_date + timedelta(days=30 * self.frequency_value)

    def create_maintenance_log(self, created_by=None):
        """Create a maintenance log entry from this schedule."""
        maintenance_log = MaintenanceLog.objects.create(
            title=self.name,
            description=self.description,
            maintenance_type=MaintenanceType.PREVENTIVE,
            property_type=self.property_type,
            property_location=self.property_location,
            equipment_name=self.equipment_name,
            scheduled_date=self.next_due_date,
            estimated_duration=self.estimated_duration,
            cost=self.estimated_cost,
            materials_used=self.materials_needed,
            tools_used=self.tools_needed,
            notes=self.instructions,
            performed_by=self.assigned_to,
            requested_by=created_by or self.assigned_to,
            cluster=self.cluster,
            created_by=created_by.id if created_by else None,
        )

        # Update next due date
        self.next_due_date = self.calculate_next_due_date()
        self.save()

        return maintenance_log

