"""
Announcement Interaction models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class AnnouncementView(AbstractClusterModel):
    """
    Model to track announcement views by users.
    """
    announcement = models.ForeignKey(
        verbose_name=_("announcement"),
        to="common.Announcement",
        on_delete=models.CASCADE,
        related_name="views",
        help_text=_("The announcement that was viewed")
    )
    user_id = models.UUIDField(
        verbose_name=_("user ID"),
        help_text=_("ID of the user who viewed the announcement")
    )
    viewed_at = models.DateTimeField(
        verbose_name=_("viewed at"),
        auto_now_add=True,
        help_text=_("When the announcement was viewed")
    )

    class Meta:
        verbose_name = _("announcement view")
        verbose_name_plural = _("announcement views")
        unique_together = ["announcement", "user_id"]
        indexes = [
            models.Index(fields=["user_id", "viewed_at"]),
        ]

    def __str__(self):
        return f"View of '{self.announcement.title}' by user {self.user_id}"


class AnnouncementLike(AbstractClusterModel):
    """
    Model to track announcement likes by users.
    """
    announcement = models.ForeignKey(
        verbose_name=_("announcement"),
        to="common.Announcement",
        on_delete=models.CASCADE,
        related_name="likes",
        help_text=_("The announcement that was liked")
    )
    user_id = models.UUIDField(
        verbose_name=_("user ID"),
        help_text=_("ID of the user who liked the announcement")
    )
    liked_at = models.DateTimeField(
        verbose_name=_("liked at"),
        auto_now_add=True,
        help_text=_("When the announcement was liked")
    )

    class Meta:
        verbose_name = _("announcement like")
        verbose_name_plural = _("announcement likes")
        unique_together = ["announcement", "user_id"]
        indexes = [
            models.Index(fields=["user_id", "liked_at"]),
        ]

    def __str__(self):
        return f"Like of '{self.announcement.title}' by user {self.user_id}"


class AnnouncementComment(AbstractClusterModel):
    """
    Model for comments on announcements.
    """
    announcement = models.ForeignKey(
        verbose_name=_("announcement"),
        to="common.Announcement",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text=_("The announcement this comment belongs to")
    )
    author_id = models.UUIDField(
        verbose_name=_("author ID"),
        help_text=_("ID of the user who created the comment")
    )
    content = models.TextField(
        verbose_name=_("content"),
        max_length=1000,
        help_text=_("Content of the comment")
    )

    class Meta:
        verbose_name = _("announcement comment")
        verbose_name_plural = _("announcement comments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["announcement", "created_at"]),
            models.Index(fields=["author_id", "created_at"]),
        ]

    def __str__(self):
        return f"Comment on '{self.announcement.title}' by user {self.author_id}"

