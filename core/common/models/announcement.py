"""
Announcement models for the ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel


class AnnouncementCategory(models.TextChoices):
    """
    Categories for announcements.
    """
    NEWS = "News", _("News")
    ESTATE_ISSUES = "Estate Issues", _("Estate Issues")
    OTHERS = "Others", _("Others")


class Announcement(AbstractClusterModel):
    """
    Model for announcements in the estate.
    """
    title = models.CharField(
        verbose_name=_("title"),
        max_length=200,
        help_text=_("Title of the announcement")
    )
    content = models.TextField(
        verbose_name=_("content"),
        max_length=2000,
        help_text=_("Content of the announcement")
    )
    category = models.CharField(
        verbose_name=_("category"),
        max_length=20,
        choices=AnnouncementCategory.choices,
        default=AnnouncementCategory.NEWS,
        help_text=_("Category of the announcement")
    )
    author_id = models.UUIDField(
        verbose_name=_("author ID"),
        help_text=_("ID of the user who created the announcement")
    )
    
    # Engagement tracking fields
    views_count = models.PositiveIntegerField(
        verbose_name=_("views count"),
        default=0,
        help_text=_("Number of times this announcement has been viewed")
    )
    likes_count = models.PositiveIntegerField(
        verbose_name=_("likes count"),
        default=0,
        help_text=_("Number of likes this announcement has received")
    )
    comments_count = models.PositiveIntegerField(
        verbose_name=_("comments count"),
        default=0,
        help_text=_("Number of comments on this announcement")
    )
    
    # Scheduling fields
    published_at = models.DateTimeField(
        verbose_name=_("published at"),
        null=True,
        blank=True,
        help_text=_("When the announcement was published")
    )
    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
        null=True,
        blank=True,
        help_text=_("When the announcement expires")
    )
    is_published = models.BooleanField(
        verbose_name=_("is published"),
        default=True,
        help_text=_("Whether the announcement is published")
    )

    class Meta:
        verbose_name = _("announcement")
        verbose_name_plural = _("announcements")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["cluster", "category"]),
            models.Index(fields=["cluster", "is_published"]),
            models.Index(fields=["cluster", "published_at"]),
            models.Index(fields=["cluster", "expires_at"]),
            models.Index(fields=["author_id"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.cluster.name if self.cluster else 'No Cluster'}"


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
            models.Index(fields=["announcement", "user_id"]),
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
            models.Index(fields=["announcement", "user_id"]),
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
        verbose_name = _("announcement attachment")
        verbose_name_plural = _("announcement attachments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["announcement"]),
            models.Index(fields=["is_image"]),
        ]

    def __str__(self):
        return f"Attachment '{self.file_name}' for '{self.announcement.title}'"


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
        verbose_name = _("announcement read status")
        verbose_name_plural = _("announcement read statuses")
        unique_together = ["announcement", "user_id"]
        indexes = [
            models.Index(fields=["user_id", "is_read"]),
            models.Index(fields=["announcement", "is_read"]),
        ]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"'{self.announcement.title}' is {status} by user {self.user_id}"