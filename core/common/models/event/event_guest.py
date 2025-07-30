"""
Event Guest models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel


logger = logging.getLogger('clustr')


class EventGuest(AbstractClusterModel):
    """
    Model for tracking guests invited to an event.
    """

    class Status(models.TextChoices):
        INVITED = "INVITED", _("Invited")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        DECLINED = "DECLINED", _("Declined")
        ATTENDED = "ATTENDED", _("Attended")
        CANCELLED = "CANCELLED", _("Cancelled")

    event = models.ForeignKey(
        verbose_name=_("event"),
        to="common.Event",
        on_delete=models.CASCADE,
        related_name="guests",
        help_text=_("The event this guest is invited to"),
    )
    name = models.CharField(
        verbose_name=_("guest name"),
        max_length=255,
        help_text=_("Name of the guest"),
    )
    email = models.EmailField(
        verbose_name=_("email address"),
        blank=True,
        null=True,
        help_text=_("Email address of the guest"),
    )
    phone = models.CharField(
        verbose_name=_("phone number"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Phone number of the guest"),
    )
    access_code = models.CharField(
        verbose_name=_("access code"),
        max_length=10,
        unique=True,
        help_text=_("Unique access code for the guest"),
    )
    invited_by = models.UUIDField(
        verbose_name=_("invited by"),
        help_text=_("ID of the user who invited this guest"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.INVITED,
        help_text=_("Current status of the guest"),
    )
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        null=True,
        help_text=_("Additional notes about the guest"),
    )
    check_in_time = models.DateTimeField(
        verbose_name=_("check-in time"),
        blank=True,
        null=True,
        help_text=_("Time when the guest checked in"),
    )
    check_out_time = models.DateTimeField(
        verbose_name=_("check-out time"),
        blank=True,
        null=True,
        help_text=_("Time when the guest checked out"),
    )

    class Meta:
        verbose_name = _("event guest")
        verbose_name_plural = _("event guests")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["status"]),
            models.Index(fields=["invited_by"]),
            models.Index(fields=["access_code"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    def save(self, *args, **kwargs):
        # Generate access code if not provided
        if not self.access_code:
            self.access_code = self._generate_unique_access_code()
        super().save(*args, **kwargs)

    def _generate_unique_access_code(self):
        """
        Generate a unique access code for the guest.
        """
        code = CodeGenerator.generate_code(length=6)
        # Check if code already exists
        while EventGuest.objects.filter(access_code=code).exists():
            code = CodeGenerator.generate_code(length=6)
        return code