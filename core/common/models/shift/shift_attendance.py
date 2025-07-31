"""
Shift Attendance models for ClustR application.
"""
from datetime import timedelta
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.common.code_generator import CodeGenerator
from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')

def generate_task_number():
    """Generate a unique task number"""
    return f"TSK-{CodeGenerator.generate_code(length=6, include_alpha=True).upper()}"



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
        default_permissions = []
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
        
        self.save(update_fields=["overtime_hours"])
    
    def calculate_late_arrival(self):
        """Calculate late arrival minutes."""
        if self.clock_in_time and self.shift.start_time:
            if self.clock_in_time > self.shift.start_time:
                late_duration = self.clock_in_time - self.shift.start_time
                self.late_arrival_minutes = int(late_duration.total_seconds() / 60)
            else:
                self.late_arrival_minutes = 0
        
        self.save(update_fields=["late_arrival_minutes"])
    
    def calculate_early_departure(self):
        """Calculate early departure minutes."""
        if self.clock_out_time and self.shift.end_time:
            if self.clock_out_time < self.shift.end_time:
                early_duration = self.shift.end_time - self.clock_out_time
                self.early_departure_minutes = int(early_duration.total_seconds() / 60)
            else:
                self.early_departure_minutes = 0
        
        self.save()