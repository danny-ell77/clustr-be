"""
Announcement models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class AnnouncementCategory(models.TextChoices):
    """
    Categories for announcements.
    """
    GENERAL = "GENERAL", _("General")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    SECURITY = "SECURITY", _("Security")
    EVENT = "EVENT", _("Event")
    EMERGENCY = "EMERGENCY", _("Emergency")
    BILLING = "BILLING", _("Billing")
    OTHER = "OTHER", _("Other")


class AnnouncementPriority(models.TextChoices):
    """
    Priority levels for announcements.
    """
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


class AnnouncementStatus(models.TextChoices):
    """
    Status of announcements.
    """
    DRAFT = "DRAFT", _("Draft")
    PUBLISHED = "PUBLISHED", _("Published")
    ARCHIVED = "ARCHIVED", _("Archived")


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
        default=AnnouncementCategory.GENERAL,
        help_text=_("Category of the announcement")
    )
    priority = models.CharField(
        verbose_name=_("priority"),
        max_length=10,
        choices=AnnouncementPriority.choices,
        default=AnnouncementPriority.MEDIUM,
        help_text=_("Priority level of the announcement")
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=10,
        choices=AnnouncementStatus.choices,
        default=AnnouncementStatus.DRAFT,
        help_text=_("Current status of the announcement")
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
        default_permissions = []
        verbose_name = _("announcement")
        verbose_name_plural = _("announcements")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["cluster", "category"]),
            models.Index(
                name="published_announcement_idx",
                fields=["cluster", "published_at"],
                condition=models.Q(is_published=True)
            ),
            models.Index(fields=["cluster", "expires_at"]),
            models.Index(fields=["author_id"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.cluster.name if self.cluster else 'No Cluster'}"

