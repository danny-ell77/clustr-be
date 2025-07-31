"""
Announcement Tracking models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class AnnouncementReadStatus(AbstractClusterModel):
    """
    Model to track read/unread status of announcements for users.
    """
    announcement = models.ForeignKey(
        verbose_name=_("announcement"),
        to="common.Announcement",
        on_delete=models.CASCADE,
        related_name="read_statuses",
        help_text=_("The announcement")
    )
    user_id = models.UUIDField(
        verbose_name=_("user ID"),
        help_text=_("ID of the user")
    )
    is_read = models.BooleanField(
        verbose_name=_("is read"),
        default=False,
        help_text=_("Whether the user has read this announcement")
    )
    read_at = models.DateTimeField(
        verbose_name=_("read at"),
        null=True,
        blank=True,
        help_text=_("When the announcement was marked as read")
    )

    class Meta:
        default_permissions = []
        verbose_name = _("announcement read status")
        verbose_name_plural = _("announcement read statuses")
        unique_together = ["announcement", "user_id"]
        indexes = [
            models.Index(
                name="read_announcement_idx",
                fields=["user_id"],
                condition=models.Q(is_read=True)
            ),
            models.Index(
                name="unread_announcement_idx",
                fields=["user_id"],
                condition=models.Q(is_read=False)
            ),
        ]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"'{self.announcement.title}' is {status} by user {self.user_id}"