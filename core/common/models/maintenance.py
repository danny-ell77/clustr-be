"""
Maintenance logging models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from core.common.models.base import AbstractClusterModel
from core.common.code_generator import CodeGenerator


class MaintenanceType(models.TextChoices):
    """Types of maintenance activities."""

    PREVENTIVE = "PREVENTIVE", _("Preventive")
    CORRECTIVE = "CORRECTIVE", _("Corrective")
    EMERGENCY = "EMERGENCY", _("Emergency")
    ROUTINE = "ROUTINE", _("Routine")
    INSPECTION = "INSPECTION", _("Inspection")
    UPGRADE = "UPGRADE", _("Upgrade")
    OTHER = "OTHER", _("Other")


class MaintenanceStatus(models.TextChoices):
    """Status of maintenance activities."""

    SCHEDULED = "SCHEDULED", _("Scheduled")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")
    POSTPONED = "POSTPONED", _("Postponed")


class MaintenancePriority(models.TextChoices):
    """Priority levels for maintenance activities."""

    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


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


def generate_maintenance_number():
    """Generate a unique maintenance number"""
    return f"MNT-{CodeGenerator.generate_code(length=6, include_alpha=True).upper()}"


class MaintenanceLog(AbstractClusterModel):
    """
    Model representing a maintenance activity log entry.
    """

    maintenance_number = models.CharField(
        verbose_name=_("maintenance number"),
        max_length=20,
        unique=True,
        default=generate_maintenance_number,
        help_text=_("Unique maintenance number for tracking"),
    )

    title = models.CharField(
        verbose_name=_("maintenance title"),
        max_length=200,
        help_text=_("Brief title describing the maintenance activity"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Detailed description of the maintenance work performed"),
    )

    maintenance_type = models.CharField(
        verbose_name=_("maintenance type"),
        max_length=20,
        choices=MaintenanceType.choices,
        default=MaintenanceType.ROUTINE,
        help_text=_("Type of maintenance activity"),
    )

    property_type = models.CharField(
        verbose_name=_("property type"),
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.OTHER,
        help_text=_("Type of property or equipment maintained"),
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

    priority = models.CharField(
        verbose_name=_("priority"),
        max_length=10,
        choices=MaintenancePriority.choices,
        default=MaintenancePriority.MEDIUM,
        help_text=_("Priority level of the maintenance"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.SCHEDULED,
        help_text=_("Current status of the maintenance"),
    )

    performed_by = models.ForeignKey(
        verbose_name=_("performed by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_maintenance",
        help_text=_("Staff member who performed the maintenance"),
    )

    supervised_by = models.ForeignKey(
        verbose_name=_("supervised by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_maintenance",
        help_text=_("Staff member who supervised the maintenance"),
    )

    requested_by = models.ForeignKey(
        verbose_name=_("requested by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="requested_maintenance",
        help_text=_("User who requested the maintenance"),
    )

    scheduled_date = models.DateTimeField(
        verbose_name=_("scheduled date"),
        null=True,
        blank=True,
        help_text=_("Scheduled date and time for the maintenance"),
    )

    started_at = models.DateTimeField(
        verbose_name=_("started at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when maintenance was started"),
    )

    completed_at = models.DateTimeField(
        verbose_name=_("completed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when maintenance was completed"),
    )

    estimated_duration = models.DurationField(
        verbose_name=_("estimated duration"),
        null=True,
        blank=True,
        help_text=_("Estimated time to complete the maintenance"),
    )

    actual_duration = models.DurationField(
        verbose_name=_("actual duration"),
        null=True,
        blank=True,
        help_text=_("Actual time spent on the maintenance"),
    )

    cost = models.DecimalField(
        verbose_name=_("cost"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total cost of the maintenance"),
    )

    materials_used = models.TextField(
        verbose_name=_("materials used"),
        blank=True,
        help_text=_("List of materials and parts used"),
    )

    tools_used = models.TextField(
        verbose_name=_("tools used"),
        blank=True,
        help_text=_("List of tools and equipment used"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the maintenance"),
    )

    completion_notes = models.TextField(
        verbose_name=_("completion notes"),
        blank=True,
        help_text=_("Notes about maintenance completion and results"),
    )

    next_maintenance_due = models.DateTimeField(
        verbose_name=_("next maintenance due"),
        null=True,
        blank=True,
        help_text=_("When the next maintenance is due for this item"),
    )

    warranty_expiry = models.DateField(
        verbose_name=_("warranty expiry"),
        null=True,
        blank=True,
        help_text=_("Warranty expiry date for the equipment"),
    )

    is_under_warranty = models.BooleanField(
        verbose_name=_("is under warranty"),
        default=False,
        help_text=_("Whether the equipment is still under warranty"),
    )

    class Meta:
        verbose_name = _("maintenance log")
        verbose_name_plural = _("maintenance logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["maintenance_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["maintenance_type"]),
            models.Index(fields=["property_type"]),
            models.Index(fields=["performed_by"]),
            models.Index(fields=["requested_by"]),
            models.Index(fields=["scheduled_date"]),
            models.Index(fields=["next_maintenance_due"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.maintenance_number} - {self.title}"

    def clean(self):
        """Validate maintenance data."""
        super().clean()

        if self.scheduled_date and self.scheduled_date <= timezone.now():
            if self.status == MaintenanceStatus.SCHEDULED:
                raise ValidationError(
                    _("Scheduled date must be in the future for scheduled maintenance")
                )

        if self.started_at and self.completed_at:
            if self.started_at >= self.completed_at:
                raise ValidationError(_("Start time must be before completion time"))

        if self.cost and self.cost < 0:
            raise ValidationError(_("Cost cannot be negative"))

    def save(self, *args, **kwargs):
        """Override save to handle status changes and calculate duration."""
        # Track status changes
        if self.pk:
            old_instance = MaintenanceLog.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == MaintenanceStatus.IN_PROGRESS and not self.started_at:
                    self.started_at = timezone.now()
                elif (
                    self.status == MaintenanceStatus.COMPLETED and not self.completed_at
                ):
                    self.completed_at = timezone.now()

        # Calculate actual duration if both start and end times are set
        if self.started_at and self.completed_at:
            self.actual_duration = self.completed_at - self.started_at

        # Update warranty status
        if self.warranty_expiry:
            self.is_under_warranty = timezone.now().date() <= self.warranty_expiry

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if maintenance is overdue."""
        if self.status in [MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED]:
            return False
        return self.scheduled_date and timezone.now() > self.scheduled_date

    @property
    def is_due_soon(self):
        """Check if maintenance is due within next 24 hours."""
        if self.status in [MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED]:
            return False
        if not self.scheduled_date:
            return False
        now = timezone.now()
        return self.scheduled_date > now and self.scheduled_date <= now + timedelta(
            hours=24
        )

    @property
    def time_remaining(self):
        """Get time remaining until scheduled date."""
        if not self.scheduled_date or self.status in [
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.CANCELLED,
        ]:
            return None
        return self.scheduled_date - timezone.now()

    @property
    def duration_worked(self):
        """Calculate duration worked on the maintenance."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at and self.status == MaintenanceStatus.IN_PROGRESS:
            return timezone.now() - self.started_at
        return timedelta(0)

    def start_maintenance(self, started_by=None):
        """Start the maintenance work."""
        if self.status != MaintenanceStatus.SCHEDULED:
            raise ValidationError(_("Can only start scheduled maintenance"))

        self.status = MaintenanceStatus.IN_PROGRESS
        self.started_at = timezone.now()

        if started_by:
            self.last_modified_by = started_by.id

        self.save()

    def complete_maintenance(self, completion_notes="", completed_by=None):
        """Mark maintenance as completed."""
        if self.status != MaintenanceStatus.IN_PROGRESS:
            raise ValidationError(
                _("Can only complete maintenance that is in progress")
            )

        self.status = MaintenanceStatus.COMPLETED
        self.completed_at = timezone.now()
        self.completion_notes = completion_notes

        if completed_by:
            self.last_modified_by = completed_by.id

        self.save()

    def cancel_maintenance(self, reason="", cancelled_by=None):
        """Cancel the maintenance."""
        if self.status == MaintenanceStatus.COMPLETED:
            raise ValidationError(_("Cannot cancel completed maintenance"))

        self.status = MaintenanceStatus.CANCELLED
        self.notes = f"{self.notes}\n\nCancelled: {reason}".strip()

        if cancelled_by:
            self.last_modified_by = cancelled_by.id

        self.save()

    def postpone_maintenance(self, new_date, reason="", postponed_by=None):
        """Postpone the maintenance to a new date."""
        if self.status == MaintenanceStatus.COMPLETED:
            raise ValidationError(_("Cannot postpone completed maintenance"))

        old_date = self.scheduled_date
        self.scheduled_date = new_date
        self.status = MaintenanceStatus.POSTPONED
        self.notes = (
            f"{self.notes}\n\nPostponed from {old_date} to {new_date}: {reason}".strip()
        )

        if postponed_by:
            self.last_modified_by = postponed_by.id

        self.save()


class MaintenanceAttachment(AbstractClusterModel):
    """
    Model for file attachments on maintenance logs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file"),
    )

    file_url = models.URLField(
        verbose_name=_("file URL"), help_text=_("URL to access the uploaded file")
    )

    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"), help_text=_("Size of the file in bytes")
    )

    file_type = models.CharField(
        verbose_name=_("file type"),
        max_length=100,
        help_text=_("MIME type of the file"),
    )

    uploaded_by = models.ForeignKey(
        verbose_name=_("uploaded by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="maintenance_attachments",
    )

    attachment_type = models.CharField(
        verbose_name=_("attachment type"),
        max_length=20,
        choices=[
            ("BEFORE", _("Before Photo")),
            ("DURING", _("During Work")),
            ("AFTER", _("After Photo")),
            ("RECEIPT", _("Receipt")),
            ("MANUAL", _("Manual")),
            ("DIAGRAM", _("Diagram")),
            ("OTHER", _("Other")),
        ],
        default="OTHER",
        help_text=_("Type of attachment"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        help_text=_("Description of the attachment"),
    )

    class Meta:
        verbose_name = _("maintenance attachment")
        verbose_name_plural = _("maintenance attachments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Attachment for {self.maintenance_log.maintenance_number}: {self.file_name}"


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


class MaintenanceCost(AbstractClusterModel):
    """
    Model for tracking detailed maintenance costs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="cost_breakdown",
    )

    category = models.CharField(
        verbose_name=_("cost category"),
        max_length=50,
        choices=[
            ("LABOR", _("Labor")),
            ("MATERIALS", _("Materials")),
            ("EQUIPMENT", _("Equipment")),
            ("CONTRACTOR", _("Contractor")),
            ("PERMITS", _("Permits")),
            ("OTHER", _("Other")),
        ],
        default="OTHER",
        help_text=_("Category of the cost"),
    )

    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        help_text=_("Description of the cost item"),
    )

    quantity = models.DecimalField(
        verbose_name=_("quantity"),
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text=_("Quantity of the item"),
    )

    unit_cost = models.DecimalField(
        verbose_name=_("unit cost"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Cost per unit"),
    )

    total_cost = models.DecimalField(
        verbose_name=_("total cost"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total cost (quantity × unit cost)"),
    )

    vendor = models.CharField(
        verbose_name=_("vendor"),
        max_length=200,
        blank=True,
        help_text=_("Vendor or supplier name"),
    )

    receipt_number = models.CharField(
        verbose_name=_("receipt number"),
        max_length=100,
        blank=True,
        help_text=_("Receipt or invoice number"),
    )

    date_incurred = models.DateField(
        verbose_name=_("date incurred"),
        default=timezone.now,
        help_text=_("Date when the cost was incurred"),
    )

    class Meta:
        verbose_name = _("maintenance cost")
        verbose_name_plural = _("maintenance costs")
        ordering = ["date_incurred"]

    def __str__(self):
        return f"{self.maintenance_log.maintenance_number} - {self.description}: ${self.total_cost}"

    def save(self, *args, **kwargs):
        """Override save to calculate total cost."""
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class MaintenanceComment(AbstractClusterModel):
    """
    Model for comments on maintenance logs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="maintenance_comments",
    )

    content = models.TextField(
        verbose_name=_("content"), help_text=_("Content of the comment")
    )

    is_internal = models.BooleanField(
        verbose_name=_("is internal"),
        default=False,
        help_text=_("Whether this comment is internal (staff only)"),
    )

    parent = models.ForeignKey(
        verbose_name=_("parent comment"),
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    class Meta:
        verbose_name = _("maintenance comment")
        verbose_name_plural = _("maintenance comments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.maintenance_log.maintenance_number} by {self.author.name}"
