"""
Exit Request models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel


logger = logging.getLogger('clustr')


class ExitRequest(AbstractClusterModel):
    """
    Model for managing child exit requests.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        DENIED = "denied", _("Denied")
        EXPIRED = "expired", _("Expired")

    request_id = models.CharField(
        verbose_name=_("request ID"),
        max_length=20,
        unique=True,
        help_text=_("Unique identifier for the exit request"),
    )

    child = models.ForeignKey(
        verbose_name=_("child"),
        to="common.Child",
        on_delete=models.CASCADE,
        related_name="exit_requests",
        help_text=_("The child this exit request is for"),
    )

    requested_by = models.ForeignKey(
        verbose_name=_("requested by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="child_exit_requests",
        help_text=_("User who requested the exit"),
    )

    reason = models.TextField(
        verbose_name=_("reason for exit"),
        help_text=_("Reason for the child's exit"),
    )

    expected_return_time = models.DateTimeField(
        verbose_name=_("expected return time"),
        help_text=_("Expected time for the child to return"),
    )

    destination = models.CharField(
        verbose_name=_("destination"),
        max_length=200,
        blank=True,
        help_text=_("Where the child is going"),
    )

    accompanying_adult = models.CharField(
        verbose_name=_("accompanying adult"),
        max_length=100,
        blank=True,
        help_text=_("Name of the adult accompanying the child"),
    )

    accompanying_adult_phone = models.CharField(
        verbose_name=_("accompanying adult phone"),
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=_(
                    "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
                ),
            )
        ],
        help_text=_("Phone number of the accompanying adult"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Current status of the exit request"),
    )

    approved_by = models.ForeignKey(
        verbose_name=_("approved by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="approved_exit_requests",
        null=True,
        blank=True,
        help_text=_("User who approved the exit request"),
    )

    approved_at = models.DateTimeField(
        verbose_name=_("approved at"),
        null=True,
        blank=True,
        help_text=_("When the exit request was approved"),
    )

    denied_by = models.ForeignKey(
        verbose_name=_("denied by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="denied_exit_requests",
        null=True,
        blank=True,
        help_text=_("User who denied the exit request"),
    )

    denied_at = models.DateTimeField(
        verbose_name=_("denied at"),
        null=True,
        blank=True,
        help_text=_("When the exit request was denied"),
    )

    denial_reason = models.TextField(
        verbose_name=_("denial reason"),
        blank=True,
        help_text=_("Reason for denying the exit request"),
    )

    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
        help_text=_("When the exit request expires"),
    )

    class Meta:
        verbose_name = _("Exit Request")
        verbose_name_plural = _("Exit Requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "child"]),
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "requested_by"]),
            models.Index(fields=["cluster", "created_at"]),
        ]

    def __str__(self):
        return f"Exit Request {self.request_id} for {self.child.name}"

    def save(self, *args, **kwargs):
        """Generate request ID if not provided"""
        if not self.request_id:
            self.request_id = f"EXIT-{CodeGenerator.generate_code(length=8, include_alpha=True).upper()}"
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the exit request has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_pending(self):
        """Check if the exit request is still pending"""
        return self.status == self.Status.PENDING and not self.is_expired

    def approve(self, user):
        """Approve the exit request"""
        from django.utils import timezone
        
        if self.status == self.Status.PENDING and not self.is_expired:
            self.status = self.Status.APPROVED
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save(update_fields=["status", "approved_by", "approved_at"])
            return True
        return False

    def deny(self, user, reason=""):
        """Deny the exit request"""
        from django.utils import timezone
        
        if self.status == self.Status.PENDING:
            self.status = self.Status.DENIED
            self.denied_by = user
            self.denied_at = timezone.now()
            self.denial_reason = reason
            self.save(update_fields=["status", "denied_by", "denied_at", "denial_reason"])
            return True
        return False

