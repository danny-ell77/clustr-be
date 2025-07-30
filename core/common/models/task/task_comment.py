"""
Task Comment models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class TaskComment(AbstractClusterModel):
    """
    Model for comments on tasks.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_comments",
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
        verbose_name = _("task comment")
        verbose_name_plural = _("task comments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.task.task_number} by {self.author.name}"
