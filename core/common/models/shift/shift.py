"""
Shift models for ClustR application.
"""

import logging
from datetime import timedelta
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class ShiftStatus(models.TextChoices):
    """Status of a shift."""
    SCHEDULED = "SCHEDULED", _("Scheduled")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")
    NO_SHOW = "NO_SHOW", _("No Show")


class ShiftType(models.TextChoices):
    """Types of shifts available."""
    SECURITY = "SECURITY", _("Security")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    CLEANING = "CLEANING", _("Cleaning")
    RECEPTION = "RECEPTION", _("Reception")
    GARDENING = "GARDENING", _("Gardening")
    OTHER = "OTHER", _("Other")


class Shift(AbstractClusterModel):
    """
    Model representing a work shift.
    """
    title = models.CharField(
        verbose_name=_("shift title"),
        max_length=200,
        help_text=_("Title or description of the shift")
    )
    
    shift_type = models.CharField(
        verbose_name=_("shift type"),
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.OTHER,
        help_text=_("Type of work shift")
    )
    
    assigned_staff = models.ForeignKey(
        verbose_name=_("assigned staff"),
        to="common.Staff",
        on_delete=models.CASCADE,
        related_name="assigned_shifts",
        help_text=_("Staff member assigned to this shift")
    )

    
    start_time = models.DateTimeField(
        verbose_name=_("start time"),
        help_text=_("Scheduled start time of the shift")
    )
    
    end_time = models.DateTimeField(
        verbose_name=_("end time"),
        help_text=_("Scheduled end time of the shift")
    )
    
    actual_start_time = models.DateTimeField(
        verbose_name=_("actual start time"),
        null=True,
        blank=True,
        help_text=_("Actual time the staff clocked in")
    )
    
    actual_end_time = models.DateTimeField(
        verbose_name=_("actual end time"),
        null=True,
        blank=True,
        help_text=_("Actual time the staff clocked out")
    )
    
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=ShiftStatus.choices,
        default=ShiftStatus.SCHEDULED,
        help_text=_("Current status of the shift")
    )
    
    location = models.CharField(
        verbose_name=_("location"),
        max_length=200,
        blank=True,
        help_text=_("Location where the shift takes place")
    )
    
    responsibilities = models.TextField(
        verbose_name=_("responsibilities"),
        blank=True,
        help_text=_("Description of responsibilities for this shift")
    )
    
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the shift")
    )
    
    is_recurring = models.BooleanField(
        verbose_name=_("is recurring"),
        default=False,
        help_text=_("Whether this shift repeats")
    )
    
    recurrence_pattern = models.CharField(
        verbose_name=_("recurrence pattern"),
        max_length=50,
        blank=True,
        help_text=_("Pattern for recurring shifts (daily, weekly, monthly)")
    )
    
    class Meta:
        default_permissions = []
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["start_time", "end_time"]),
            models.Index(fields=["assigned_staff", "start_time"]),
            models.Index(fields=["status"]),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.assigned_staff.name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    def clean(self):
        """Validate shift data."""
        super().clean()
        
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError(_("Start time must be before end time"))
            
            # Check for overlapping shifts for the same staff member
            overlapping_shifts = Shift.objects.filter(
                cluster=self.cluster,
                assigned_staff=self.assigned_staff,
                status__in=[ShiftStatus.SCHEDULED, ShiftStatus.IN_PROGRESS]
            ).exclude(id=self.id)
            
            for shift in overlapping_shifts:
                if (self.start_time < shift.end_time and self.end_time > shift.start_time):
                    raise ValidationError(
                        _("This shift overlaps with another shift for the same staff member: %(shift)s") % {
                            'shift': shift.title
                        }
                    )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Calculate scheduled duration of the shift."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return timedelta(0)
    
    @property
    def actual_duration(self):
        """Calculate actual duration worked."""
        if self.actual_start_time and self.actual_end_time:
            return self.actual_end_time - self.actual_start_time
        return timedelta(0)
    
    @property
    def is_overdue(self):
        """Check if shift is overdue (past end time and not completed)."""
        if self.status in [ShiftStatus.COMPLETED, ShiftStatus.CANCELLED]:
            return False
        return timezone.now() > self.end_time
    
    @property
    def is_upcoming(self):
        """Check if shift is upcoming (starts within next 24 hours)."""
        if self.status != ShiftStatus.SCHEDULED:
            return False
        now = timezone.now()
        return self.start_time > now and self.start_time <= now + timedelta(hours=24)
    
    def clock_in(self, clock_in_time=None):
        """Clock in for the shift."""
        if self.status != ShiftStatus.SCHEDULED:
            raise ValidationError(_("Can only clock in for scheduled shifts"))
        
        self.actual_start_time = clock_in_time or timezone.now()
        self.status = ShiftStatus.IN_PROGRESS
        self.save(update_fields=["actual_start_time", "status"])
    
    def clock_out(self, clock_out_time=None):
        """Clock out from the shift."""
        if self.status != ShiftStatus.IN_PROGRESS:
            raise ValidationError(_("Can only clock out from shifts in progress"))
        
        self.actual_end_time = clock_out_time or timezone.now()
        self.status = ShiftStatus.COMPLETED
        self.save(update_fields=["actual_end_time", "status"])
    
    def mark_no_show(self):
        """Mark shift as no show."""
        if self.status != ShiftStatus.SCHEDULED:
            raise ValidationError(_("Can only mark scheduled shifts as no show"))
        
        self.status = ShiftStatus.NO_SHOW
        self.save(update_fields=["status"])
    
    def cancel(self):
        """Cancel the shift."""
        if self.status in [ShiftStatus.COMPLETED, ShiftStatus.NO_SHOW]:
            raise ValidationError(_("Cannot cancel completed or no-show shifts"))
        
        self.status = ShiftStatus.CANCELLED
        self.save(update_fields=["status"])

