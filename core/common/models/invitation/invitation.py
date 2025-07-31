"""
Invitation models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class Invitation(AbstractClusterModel):
    """
    Invitation model for managing recurring visitor invitations.
    """

    class RecurrenceType(models.TextChoices):
        NONE = "NONE", _("None (One-time)")
        DAILY = "DAILY", _("Daily")
        WEEKLY = "WEEKLY", _("Weekly")
        MONTHLY = "MONTHLY", _("Monthly")
        CUSTOM = "CUSTOM", _("Custom")

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        REVOKED = "REVOKED", _("Revoked")
        EXPIRED = "EXPIRED", _("Expired")
        COMPLETED = "COMPLETED", _("Completed")

    visitor = models.ForeignKey(
        verbose_name=_("visitor"),
        to="common.Visitor",
        on_delete=models.CASCADE,
        related_name="invitations",
        help_text=_("The visitor this invitation is for"),
    )
    title = models.CharField(
        verbose_name=_("title"),
        max_length=255,
        help_text=_("Title or purpose of the invitation"),
    )
    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
        help_text=_("Detailed description of the invitation"),
    )
    start_date = models.DateField(
        verbose_name=_("start date"),
        help_text=_("Date when the invitation becomes valid"),
    )
    end_date = models.DateField(
        verbose_name=_("end date"),
        help_text=_("Date when the invitation expires"),
    )
    recurrence_type = models.CharField(
        verbose_name=_("recurrence type"),
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        help_text=_("Type of recurrence for this invitation"),
    )
    recurrence_days = models.CharField(
        verbose_name=_("recurrence days"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Days of the week for weekly recurrence (comma-separated numbers, 0=Monday)"),
    )
    recurrence_day_of_month = models.IntegerField(
        verbose_name=_("recurrence day of month"),
        blank=True,
        null=True,
        help_text=_("Day of the month for monthly recurrence"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_("Current status of the invitation"),
    )
    created_by = models.UUIDField(
        verbose_name=_("created by"),
        help_text=_("ID of the user who created this invitation"),
    )
    revoked_by = models.UUIDField(
        verbose_name=_("revoked by"),
        blank=True,
        null=True,
        help_text=_("ID of the user who revoked this invitation"),
    )
    revoked_at = models.DateTimeField(
        verbose_name=_("revoked at"),
        blank=True,
        null=True,
        help_text=_("Date and time when the invitation was revoked"),
    )
    revocation_reason = models.TextField(
        verbose_name=_("revocation reason"),
        blank=True,
        null=True,
        help_text=_("Reason for revoking the invitation"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("invitation")
        verbose_name_plural = _("invitations")
        ordering = ["-start_date", "status"]
        indexes = [
            models.Index(fields=["visitor"]),
            models.Index(fields=["status"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["recurrence_type"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.visitor.name} ({self.get_status_display()})"