"""
Maintenance Comment models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class MaintenanceComment(AbstractClusterModel):
    """
    Model for comments on maintenance logs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="maintenance_comments",
    )

    content = models.TextField(
        verbose_name=_("content"), help_text=_("Content of the comment")
    )

    is_internal = models.BooleanField(
        verbose_name=_("is internal"),
        default=False,
        help_text=_("Whether this comment is internal (staff only)"),
    )

    parent = models.ForeignKey(
        verbose_name=_("parent comment"),
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    class Meta:
        default_permissions = []
        verbose_name = _("maintenance comment")
        verbose_name_plural = _("maintenance comments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.maintenance_log.maintenance_number} by {self.author.name}"
