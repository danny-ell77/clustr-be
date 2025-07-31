"""
Visitor Log models for ClustR application.
"""

import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

# Related model imports (will be converted to string references)
# from core.common.models.visitor.unknown import LogType

logger = logging.getLogger('clustr')


class VisitorLog(AbstractClusterModel):
    """
    Log of visitor entry and exit events.
    """

    class LogType(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        CHECKED_IN = "CHECKED_IN", _("Checked-in")
        CHECKED_OUT = "CHECKED_OUT", _("Checked-out")
        CANCELLED = "CANCELLED", _("Cancelled")

    visitor = models.ForeignKey(
        verbose_name=_("visitor"),
        to="common.Visitor",
        on_delete=models.CASCADE,
        related_name="logs",
        help_text=_("The visitor this log entry is for"),
    )
    date = models.DateField(
        verbose_name=_("date"),
        auto_now_add=True,
        help_text=_("Date of the log entry"),
    )
    arrival_time = models.TimeField(
        verbose_name=_("arrival time"),
        null=True,
        blank=True,
        help_text=_("Time when the visitor arrived"),
    )
    departure_time = models.TimeField(
        verbose_name=_("departure time"),
        null=True,
        blank=True,
        help_text=_("Time when the visitor departed"),
    )
    log_type = models.CharField(
        verbose_name=_("log type"),
        max_length=20,
        choices=LogType.choices,
        default=LogType.SCHEDULED,
        help_text=_("Type of log entry"),
    )
    checked_in_by = models.UUIDField(
        verbose_name=_("checked in by"),
        null=True,
        blank=True,
        help_text=_("ID of the user who checked in the visitor"),
    )
    checked_out_by = models.UUIDField(
        verbose_name=_("checked out by"),
        null=True,
        blank=True,
        help_text=_("ID of the user who checked out the visitor"),
    )
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        null=True,
        help_text=_("Additional notes about the visit"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("visitor log")
        verbose_name_plural = _("visitor logs")
        ordering = ["-date", "-arrival_time"]
        indexes = [
            models.Index(fields=["visitor"]),
            models.Index(fields=["date"]),
            models.Index(fields=["log_type"]),
        ]

    def __str__(self):
        return f"{self.visitor.name} - {self.get_log_type_display()} on {self.date}"