"""
Issue Comment models for ClustR application.
"""

import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class IssueComment(AbstractClusterModel):
    """
    Model for comments on issue tickets.
    """
    
    issue = models.ForeignKey(
        verbose_name=_("issue"),
        to="common.IssueTicket",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text=_("The issue this comment belongs to"),
    )
    
    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="issue_comments",
        help_text=_("User who wrote the comment"),
    )
    
    content = models.TextField(
        verbose_name=_("content"),
        help_text=_("Content of the comment"),
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
        help_text=_("Parent comment for threaded discussions"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("issue comment")
        verbose_name_plural = _("issue comments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["author"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_internal"]),
        ]

    def __str__(self):
        return f"Comment on {self.issue.issue_no} by {self.author.name}"

