"""
Entry Exit Log models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class EntryExitLog(AbstractClusterModel):
    """
    Model for tracking child entry and exit events.
    """

    class LogType(models.TextChoices):
        EXIT = "exit", _("Exit")
        ENTRY = "entry", _("Entry")

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        OVERDUE = "overdue", _("Overdue")

    child = models.ForeignKey(
        verbose_name=_("child"),
        to="common.Child",
        on_delete=models.CASCADE,
        related_name="entry_exit_logs",
        help_text=_("The child this log entry is for"),
    )

    exit_request = models.ForeignKey(
        verbose_name=_("exit request"),
        to="common.ExitRequest",
        on_delete=models.CASCADE,
        related_name="logs",
        null=True,
        blank=True,
        help_text=_("The exit request associated with this log"),
    )

    log_type = models.CharField(
        verbose_name=_("log type"),
        max_length=10,
        choices=LogType.choices,
        help_text=_("Type of log entry"),
    )

    date = models.DateField(
        verbose_name=_("date"),
        help_text=_("Date of the entry/exit"),
    )

    exit_time = models.TimeField(
        verbose_name=_("exit time"),
        null=True,
        blank=True,
        help_text=_("Time when the child exited"),
    )

    entry_time = models.TimeField(
        verbose_name=_("entry time"),
        null=True,
        blank=True,
        help_text=_("Time when the child returned"),
    )

    expected_return_time = models.DateTimeField(
        verbose_name=_("expected return time"),
        null=True,
        blank=True,
        help_text=_("Expected time for the child to return"),
    )

    actual_return_time = models.DateTimeField(
        verbose_name=_("actual return time"),
        null=True,
        blank=True,
        help_text=_("Actual time when the child returned"),
    )

    reason = models.TextField(
        verbose_name=_("reason"),
        help_text=_("Reason for the exit"),
    )

    destination = models.CharField(
        verbose_name=_("destination"),
        max_length=200,
        blank=True,
        help_text=_("Where the child went"),
    )

    accompanying_adult = models.CharField(
        verbose_name=_("accompanying adult"),
        max_length=100,
        blank=True,
        help_text=_("Name of the adult accompanying the child"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        help_text=_("Current status of the entry/exit"),
    )

    verified_by = models.ForeignKey(
        verbose_name=_("verified by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="verified_child_logs",
        null=True,
        blank=True,
        help_text=_("Security personnel who verified the exit/entry"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the entry/exit"),
    )

    class Meta:
        verbose_name = _("Entry/Exit Log")
        verbose_name_plural = _("Entry/Exit Logs")
        ordering = ["-date", "-exit_time"]
        indexes = [
            models.Index(fields=["cluster", "child"]),
            models.Index(fields=["cluster", "date"]),
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "log_type"]),
        ]

    def __str__(self):
        return f"{self.child.name} - {self.get_log_type_display()} on {self.date}"

    @property
    def is_overdue(self):
        """Check if the child is overdue for return"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.expected_return_time:
            return (
                self.status == self.Status.IN_PROGRESS and 
                timezone.now() > self.expected_return_time
            )
        return False

    @property
    def duration_minutes(self):
        """Calculate the duration of the exit in minutes"""
        if self.exit_time and self.entry_time:
            from datetime import datetime, timedelta
            
            # Combine date with times
            exit_datetime = datetime.combine(self.date, self.exit_time)
            
            # Handle case where entry is on the next day
            entry_date = self.date
            if self.entry_time < self.exit_time:
                entry_date = self.date + timedelta(days=1)
            
            entry_datetime = datetime.combine(entry_date, self.entry_time)
            
            return int((entry_datetime - exit_datetime).total_seconds() / 60)
        return None

    def mark_exit(self, verified_by=None):
        """Mark the child as having exited"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.status == self.Status.SCHEDULED:
            self.status = self.Status.IN_PROGRESS
            self.exit_time = timezone.now().time()
            if verified_by:
                self.verified_by = verified_by
            self.save(update_fields=["status", "exit_time", "verified_by"])
            return True
        return False

    def mark_entry(self, verified_by=None):
        """Mark the child as having returned"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.COMPLETED
            self.entry_time = timezone.now().time()
            self.actual_return_time = timezone.now()
            if verified_by:
                self.verified_by = verified_by
            self.save(update_fields=["status", "entry_time", "actual_return_time", "verified_by"])
            return True
        return False

    def mark_overdue(self):
        """Mark the child as overdue"""
        if self.is_overdue and self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.OVERDUE
            self.save(update_fields=["status"])
            return True
        return False