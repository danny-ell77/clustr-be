"""
Announcement Content models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class AnnouncementAttachment(AbstractClusterModel):
    """
    Model for attachments to announcements.
    """
    announcement = models.ForeignKey(
        verbose_name=_("announcement"),
        to="common.Announcement",
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text=_("The announcement this attachment belongs to")
    )
    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file")
    )
    file_url = models.URLField(
        verbose_name=_("file URL"),
        help_text=_("URL to access the uploaded file")
    )
    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"),
        help_text=_("Size of the file in bytes")
    )
    file_type = models.CharField(
        verbose_name=_("file type"),
        max_length=100,
        help_text=_("MIME type of the file")
    )
    is_image = models.BooleanField(
        verbose_name=_("is image"),
        default=False,
        help_text=_("Whether this attachment is an image")
    )

    class Meta:
        default_permissions = []
        verbose_name = _("announcement attachment")
        verbose_name_plural = _("announcement attachments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["announcement"]),
            models.Index(
                name="image_attachment_idx",
                fields=["announcement"],
                condition=models.Q(is_image=True)
            ),
        ]

    def __str__(self):
        return f"Attachment '{self.file_name}' for '{self.announcement.title}'"

