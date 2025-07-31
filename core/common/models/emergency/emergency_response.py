"""
Emergency Response models for ClustR application.
"""
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class EmergencyResponse(AbstractClusterModel):
    """
    Model for tracking emergency response activities.
    """

    alert = models.ForeignKey(
        verbose_name=_("alert"),
        to="common.SOSAlert",
        on_delete=models.CASCADE,
        related_name="responses",
        help_text=_("The alert this response is for"),
    )

    responder = models.ForeignKey(
        verbose_name=_("responder"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="emergency_responses",
        help_text=_("User who responded"),
    )

    response_type = models.CharField(
        verbose_name=_("response type"),
        max_length=20,
        choices=[
            ("acknowledged", _("Acknowledged")),
            ("dispatched", _("Dispatched")),
            ("on_scene", _("On Scene")),
            ("resolved", _("Resolved")),
            ("cancelled", _("Cancelled")),
        ],
        help_text=_("Type of response"),
    )

    notes = models.TextField(
        verbose_name=_("notes"), blank=True, help_text=_("Response notes")
    )

    estimated_arrival = models.DateTimeField(
        verbose_name=_("estimated arrival"),
        null=True,
        blank=True,
        help_text=_("Estimated arrival time"),
    )

    actual_arrival = models.DateTimeField(
        verbose_name=_("actual arrival"),
        null=True,
        blank=True,
        help_text=_("Actual arrival time"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("Emergency Response")
        verbose_name_plural = _("Emergency Responses")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "alert"]),
            models.Index(fields=["cluster", "responder"]),
        ]

    def __str__(self):
        return f"Response to {self.alert.alert_id} by {self.responder.name}"
