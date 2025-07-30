"""
Issue Attachment models for ClustR application.
"""

import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class IssueAttachment(AbstractClusterModel):
    """
    Model for file attachments on issue tickets and comments.
    """
    
    issue = models.ForeignKey(
        verbose_name=_("issue"),
        to="common.IssueTicket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        help_text=_("The issue this attachment belongs to"),
    )
    
    comment = models.ForeignKey(
        verbose_name=_("comment"),
        to="common.IssueComment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        help_text=_("The comment this attachment belongs to"),
    )
    
    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file"),
    )
    
    file_url = models.URLField(
        verbose_name=_("file URL"),
        help_text=_("URL to access the uploaded file"),
    )
    
    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"),
        help_text=_("Size of the file in bytes"),
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
        related_name="issue_attachments",
        help_text=_("User who uploaded the file"),
    )

    class Meta:
        verbose_name = _("issue attachment")
        verbose_name_plural = _("issue attachments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["comment"]),
            models.Index(fields=["uploaded_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(issue__isnull=False) | models.Q(comment__isnull=False),
                name="attachment_belongs_to_issue_or_comment"
            )
        ]

    def __str__(self):
        if self.issue:
            return f"Attachment for {self.issue.issue_no}: {self.file_name}"
        elif self.comment:
            return f"Attachment for comment on {self.comment.issue.issue_no}: {self.file_name}"
        return f"Attachment: {self.file_name}"

