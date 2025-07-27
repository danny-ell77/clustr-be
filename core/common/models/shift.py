"""
Shift management models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

from core.common.models.base import AbstractClusterModel


class ShiftType(models.TextChoices):
    """Types of shifts available."""
    SECURITY = "SECURITY", _("Security")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    CLEANING = "CLEANING", _("Cleaning")
    RECEPTION = "RECEPTION", _("Reception")
    GARDENING = "GARDENING", _("Gardening")
    OTHER = "OTHER", _("Other")


class ShiftStatus(models.TextChoices):
    """Status of a shift."""
    SCHEDULED = "SCHEDULED", _("Scheduled")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")
    NO_SHOW = "NO_SHOW", _("No Show")


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
        to="accounts.AccountUser",
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
        self.save()
    
    def clock_out(self, clock_out_time=None):
        """Clock out from the shift."""
        if self.status != ShiftStatus.IN_PROGRESS:
            raise ValidationError(_("Can only clock out from shifts in progress"))
        
        self.actual_end_time = clock_out_time or timezone.now()
        self.status = ShiftStatus.COMPLETED
        self.save()
    
    def mark_no_show(self):
        """Mark shift as no show."""
        if self.status != ShiftStatus.SCHEDULED:
            raise ValidationError(_("Can only mark scheduled shifts as no show"))
        
        self.status = ShiftStatus.NO_SHOW
        self.save()
    
    def cancel(self):
        """Cancel the shift."""
        if self.status in [ShiftStatus.COMPLETED, ShiftStatus.NO_SHOW]:
            raise ValidationError(_("Cannot cancel completed or no-show shifts"))
        
        self.status = ShiftStatus.CANCELLED
        self.save()


class ShiftSwapRequest(AbstractClusterModel):
    """
    Model for handling shift swap requests between staff members.
    """
    
    class SwapStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CANCELLED = "CANCELLED", _("Cancelled")
    
    original_shift = models.ForeignKey(
        verbose_name=_("original shift"),
        to="common.Shift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_original"
    )
    
    requested_by = models.ForeignKey(
        verbose_name=_("requested by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="shift_swap_requests"
    )
    
    requested_with = models.ForeignKey(
        verbose_name=_("requested with"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="shift_swap_offers"
    )
    
    target_shift = models.ForeignKey(
        verbose_name=_("target shift"),
        to="common.Shift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_target",
        null=True,
        blank=True,
        help_text=_("The shift to swap with (optional for coverage requests)")
    )
    
    reason = models.TextField(
        verbose_name=_("reason"),
        help_text=_("Reason for the swap request")
    )
    
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=SwapStatus.choices,
        default=SwapStatus.PENDING
    )
    
    approved_by = models.ForeignKey(
        verbose_name=_("approved by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_shift_swaps"
    )
    
    approved_at = models.DateTimeField(
        verbose_name=_("approved at"),
        null=True,
        blank=True
    )
    
    response_message = models.TextField(
        verbose_name=_("response message"),
        blank=True,
        help_text=_("Response message from the other staff member or admin")
    )
    
    class Meta:
        verbose_name = _("shift swap request")
        verbose_name_plural = _("shift swap requests")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Swap request: {self.original_shift.title} by {self.requested_by.name}"
    
    def approve(self, approved_by, response_message=""):
        """Approve the swap request."""
        if self.status != self.SwapStatus.PENDING:
            raise ValidationError(_("Can only approve pending requests"))
        
        self.status = self.SwapStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.response_message = response_message
        self.save()
        
        # Perform the actual swap
        if self.target_shift:
            # Swap the assigned staff
            original_staff = self.original_shift.assigned_staff
            target_staff = self.target_shift.assigned_staff
            
            self.original_shift.assigned_staff = target_staff
            self.target_shift.assigned_staff = original_staff
            
            self.original_shift.save()
            self.target_shift.save()
        else:
            # Just reassign the original shift
            self.original_shift.assigned_staff = self.requested_with
            self.original_shift.save()
    
    def reject(self, rejected_by, response_message=""):
        """Reject the swap request."""
        if self.status != self.SwapStatus.PENDING:
            raise ValidationError(_("Can only reject pending requests"))
        
        self.status = self.SwapStatus.REJECTED
        self.approved_by = rejected_by
        self.approved_at = timezone.now()
        self.response_message = response_message
        self.save()


class ShiftAttendance(AbstractClusterModel):
    """
    Model for tracking detailed attendance information for shifts.
    """
    
    shift = models.OneToOneField(
        verbose_name=_("shift"),
        to="common.Shift",
        on_delete=models.CASCADE,
        related_name="attendance"
    )
    
    clock_in_time = models.DateTimeField(
        verbose_name=_("clock in time"),
        null=True,
        blank=True
    )
    
    clock_out_time = models.DateTimeField(
        verbose_name=_("clock out time"),
        null=True,
        blank=True
    )
    
    break_start_time = models.DateTimeField(
        verbose_name=_("break start time"),
        null=True,
        blank=True
    )
    
    break_end_time = models.DateTimeField(
        verbose_name=_("break end time"),
        null=True,
        blank=True
    )
    
    total_break_duration = models.DurationField(
        verbose_name=_("total break duration"),
        default=timedelta(0),
        help_text=_("Total time spent on breaks")
    )
    
    overtime_hours = models.DurationField(
        verbose_name=_("overtime hours"),
        default=timedelta(0),
        help_text=_("Hours worked beyond scheduled time")
    )
    
    late_arrival_minutes = models.PositiveIntegerField(
        verbose_name=_("late arrival minutes"),
        default=0,
        help_text=_("Minutes late for shift start")
    )
    
    early_departure_minutes = models.PositiveIntegerField(
        verbose_name=_("early departure minutes"),
        default=0,
        help_text=_("Minutes left before shift end")
    )
    
    attendance_notes = models.TextField(
        verbose_name=_("attendance notes"),
        blank=True,
        help_text=_("Notes about attendance issues or special circumstances")
    )
    
    class Meta:
        verbose_name = _("shift attendance")
        verbose_name_plural = _("shift attendances")
    
    def __str__(self):
        return f"Attendance for {self.shift.title}"
    
    @property
    def actual_work_duration(self):
        """Calculate actual work time excluding breaks."""
        if self.clock_in_time and self.clock_out_time:
            total_time = self.clock_out_time - self.clock_in_time
            return total_time - self.total_break_duration
        return timedelta(0)
    
    def calculate_overtime(self):
        """Calculate overtime hours."""
        if self.clock_out_time and self.shift.end_time:
            if self.clock_out_time > self.shift.end_time:
                self.overtime_hours = self.clock_out_time - self.shift.end_time
            else:
                self.overtime_hours = timedelta(0)
        
        self.save()
    
    def calculate_late_arrival(self):
        """Calculate late arrival minutes."""
        if self.clock_in_time and self.shift.start_time:
            if self.clock_in_time > self.shift.start_time:
                late_duration = self.clock_in_time - self.shift.start_time
                self.late_arrival_minutes = int(late_duration.total_seconds() / 60)
            else:
                self.late_arrival_minutes = 0
        
        self.save()
    
    def calculate_early_departure(self):
        """Calculate early departure minutes."""
        if self.clock_out_time and self.shift.end_time:
            if self.clock_out_time < self.shift.end_time:
                early_duration = self.shift.end_time - self.clock_out_time
                self.early_departure_minutes = int(early_duration.total_seconds() / 60)
            else:
                self.early_departure_minutes = 0
        
        self.save()