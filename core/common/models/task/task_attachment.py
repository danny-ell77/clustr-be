"""
Task Attachment models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class TaskAttachment(AbstractClusterModel):
    """
    Model for file attachments on tasks.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
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
        related_name="task_attachments",
    )

    attachment_type = models.CharField(
        verbose_name=_("attachment type"),
        max_length=20,
        choices=[
            ("INSTRUCTION", _("Instruction")),
            ("REFERENCE", _("Reference")),
            ("EVIDENCE", _("Evidence")),
            ("COMPLETION", _("Completion")),
            ("OTHER", _("Other")),
        ],
        default="OTHER",
        help_text=_("Type of attachment"),
    )

    class Meta:
        verbose_name = _("task attachment")
        verbose_name_plural = _("task attachments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Attachment for {self.task.task_number}: {self.file_name}"

