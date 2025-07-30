"""
Maintenance Attachment models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class MaintenanceAttachment(AbstractClusterModel):
    """
    Model for file attachments on maintenance logs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file"),
    )

    file_url = models.URLField(
        verbose_name=_("file URL"), help_text=_("URL to access the uploaded file")
    )

    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"), help_text=_("Size of the file in bytes")
    )

    file_type = models.CharField(
        verbose_name=_("file type"),
        max_length=100,
        help_text=_("MIME type of the file"),
    )

    uploaded_by = models.ForeignKey(
        verbose_name=_("uploaded by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="maintenance_attachments",
    )

    attachment_type = models.CharField(
        verbose_name=_("attachment type"),
        max_length=20,
        choices=[
            ("BEFORE", _("Before Photo")),
            ("DURING", _("During Work")),
            ("AFTER", _("After Photo")),
            ("RECEIPT", _("Receipt")),
            ("MANUAL", _("Manual")),
            ("DIAGRAM", _("Diagram")),
            ("OTHER", _("Other")),
        ],
        default="OTHER",
        help_text=_("Type of attachment"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        help_text=_("Description of the attachment"),
    )

    class Meta:
        verbose_name = _("maintenance attachment")
        verbose_name_plural = _("maintenance attachments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Attachment for {self.maintenance_log.maintenance_number}: {self.file_name}"

