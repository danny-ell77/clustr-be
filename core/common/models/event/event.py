"""
Event models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class Event(AbstractClusterModel):
    """
    Event model for managing estate events and bulk invitations.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        PUBLISHED = "PUBLISHED", _("Published")
        CANCELLED = "CANCELLED", _("Cancelled")
        COMPLETED = "COMPLETED", _("Completed")

    title = models.CharField(
        verbose_name=_("title"),
        max_length=255,
        help_text=_("Title of the event"),
    )
    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
        help_text=_("Detailed description of the event"),
    )
    event_date = models.DateField(
        verbose_name=_("event date"),
        help_text=_("Date of the event"),
    )
    event_time = models.TimeField(
        verbose_name=_("event time"),
        help_text=_("Start time of the event"),
    )
    end_time = models.TimeField(
        verbose_name=_("end time"),
        blank=True,
        null=True,
        help_text=_("End time of the event"),
    )
    location = models.CharField(
        verbose_name=_("location"),
        max_length=255,
        help_text=_("Location of the event"),
    )
    access_code = models.CharField(
        verbose_name=_("access code"),
        max_length=10,
        unique=True,
        help_text=_("Unique access code for the event"),
    )
    max_guests = models.PositiveIntegerField(
        verbose_name=_("maximum guests"),
        default=0,
        help_text=_("Maximum number of guests allowed (0 for unlimited)"),
    )
    guests_added = models.PositiveIntegerField(
        verbose_name=_("guests added"),
        default=0,
        help_text=_("Number of guests added to the event"),
    )
    created_by = models.UUIDField(
        verbose_name=_("created by"),
        help_text=_("ID of the user who created this event"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text=_("Current status of the event"),
    )
    is_public = models.BooleanField(
        verbose_name=_("is public"),
        default=False,
        help_text=_("Whether the event is public or private"),
    )
    requires_approval = models.BooleanField(
        verbose_name=_("requires approval"),
        default=False,
        help_text=_("Whether guests require approval to attend"),
    )

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")
        ordering = ["-event_date", "-event_time"]
        indexes = [
            models.Index(fields=["event_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["access_code"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.event_date})"

    def save(self, *args, **kwargs):
        # Generate access code if not provided
        if not self.access_code:
            self.access_code = self._generate_unique_access_code()
        super().save(*args, **kwargs)

    def _generate_unique_access_code(self):
        """
        Generate a unique access code for the event.
        """
        code = CodeGenerator.generate_code(length=6, include_alpha=True)
        # Check if code already exists
        while Event.objects.filter(access_code=code).exists():
            code = CodeGenerator.generate_code(length=6, include_alpha=True)
        return code

