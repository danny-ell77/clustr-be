"""
Visitor management models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.code_generator import CodeGenerator
from core.common.models.base import AbstractClusterModel


class Visitor(AbstractClusterModel):
    """
    Visitor model for managing guest access to estates.
    """

    class VisitType(models.TextChoices):
        ONE_TIME = "ONE_TIME", _("One-time")
        SHORT_STAY = "SHORT_STAY", _("Short stay")
        EXTENDED_STAY = "EXTENDED_STAY", _("Extended stay")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CHECKED_IN = "CHECKED_IN", _("Checked-in")
        CHECKED_OUT = "CHECKED_OUT", _("Checked-out")
        EXPIRED = "EXPIRED", _("Expired")

    class ValidFor(models.TextChoices):
        ONE_TIME = "ONE_TIME", _("One-time")
        MULTIPLE = "MULTIPLE", _("Multiple visits")

    name = models.CharField(
        verbose_name=_("visitor name"),
        max_length=255,
        help_text=_("Full name of the visitor"),
    )
    email = models.EmailField(
        verbose_name=_("email address"),
        blank=True,
        null=True,
        help_text=_("Email address of the visitor"),
    )
    phone = models.CharField(
        verbose_name=_("phone number"),
        max_length=20,
        help_text=_("Phone number of the visitor"),
    )
    estimated_arrival = models.DateTimeField(
        verbose_name=_("estimated arrival"),
        help_text=_("Expected date and time of arrival"),
    )
    visit_type = models.CharField(
        verbose_name=_("visit type"),
        max_length=20,
        choices=VisitType.choices,
        default=VisitType.ONE_TIME,
        help_text=_("Type of visit"),
    )
    access_code = models.CharField(
        verbose_name=_("access code"),
        max_length=10,
        unique=True,
        help_text=_("Unique access code for the visitor"),
    )
    invited_by = models.UUIDField(
        verbose_name=_("invited by"),
        help_text=_("ID of the user who invited this visitor"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Current status of the visitor"),
    )
    valid_for = models.CharField(
        verbose_name=_("valid for"),
        max_length=20,
        choices=ValidFor.choices,
        default=ValidFor.ONE_TIME,
        help_text=_("Validity type of the access code"),
    )
    valid_date = models.DateField(
        verbose_name=_("valid date"),
        help_text=_("Date until which the access code is valid"),
    )
    purpose = models.TextField(
        verbose_name=_("purpose of visit"),
        blank=True,
        null=True,
        help_text=_("Purpose or reason for the visit"),
    )
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        null=True,
        help_text=_("Additional notes about the visitor"),
    )

    class Meta:
        verbose_name = _("visitor")
        verbose_name_plural = _("visitors")
        ordering = ["-estimated_arrival"]
        indexes = [
            models.Index(fields=["access_code"]),
            models.Index(fields=["invited_by"]),
            models.Index(fields=["status"]),
            models.Index(fields=["valid_date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Generate access code if not provided
        if not self.access_code:
            self.access_code = self._generate_unique_access_code()
        super().save(*args, **kwargs)

    def _generate_unique_access_code(self):
        """
        Generate a unique access code for the visitor.
        """
        code = CodeGenerator.generate_code(length=6)
        # Check if code already exists
        while Visitor.objects.filter(access_code=code).exists():
            code = CodeGenerator.generate_code(length=6)
        return code


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