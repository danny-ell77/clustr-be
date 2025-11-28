"""
Chat participant model for managing users in chat conversations.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel


class ChatParticipant(AbstractClusterModel):
    """
    Represents a user's participation in a chat conversation.
    Tracks join/leave times, permissions, and read status.
    """

    chat = models.ForeignKey(
        "common.Chat",
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name=_("Chat"),
        help_text=_("The chat this participant belongs to"),
    )

    user = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="chat_participations",
        verbose_name=_("User"),
        help_text=_("The user participating in the chat"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether the user is currently active in this chat"),
    )

    is_admin = models.BooleanField(
        default=False,
        verbose_name=_("Is Admin"),
        help_text=_("Whether the user has admin privileges in this chat"),
    )

    is_moderator = models.BooleanField(
        default=False,
        verbose_name=_("Is Moderator"),
        help_text=_("Whether the user can moderate messages in this chat"),
    )

    can_send_messages = models.BooleanField(
        default=True,
        verbose_name=_("Can Send Messages"),
        help_text=_("Whether the user can send messages in this chat"),
    )

    can_add_participants = models.BooleanField(
        default=False,
        verbose_name=_("Can Add Participants"),
        help_text=_("Whether the user can add new participants to this chat"),
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Joined At"),
        help_text=_("When the user joined this chat"),
    )

    left_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Left At"),
        help_text=_("When the user left this chat"),
    )

    last_read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last Read At"),
        help_text=_("When the user last read messages in this chat"),
    )

    last_message_read = models.ForeignKey(
        "common.Message",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="read_by_participants",
        verbose_name=_("Last Message Read"),
        help_text=_("The last message read by this participant"),
    )

    notification_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Notification Settings"),
        help_text=_("User's notification preferences for this chat"),
    )

    muted_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Muted Until"),
        help_text=_("When the chat notifications will be unmuted for this user"),
    )

    class Meta:
        verbose_name = _("Chat Participant")
        verbose_name_plural = _("Chat Participants")
        unique_together = ["chat", "user"]
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["chat", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["last_read_at"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.chat}"

    def leave_chat(self):
        """Mark the participant as having left the chat"""
        self.is_active = False
        self.left_at = timezone.now()
        self.save(update_fields=["is_active", "left_at"])

    def rejoin_chat(self):
        """Mark the participant as having rejoined the chat"""
        self.is_active = True
        self.left_at = None
        self.joined_at = timezone.now()
        self.save(update_fields=["is_active", "left_at", "joined_at"])

    def mark_as_read(self, message=None):
        """Mark messages as read up to a specific message or current time"""
        self.last_read_at = timezone.now()
        if message:
            self.last_message_read = message
            self.save(update_fields=["last_read_at", "last_message_read"])
        else:
            self.save(update_fields=["last_read_at"])

    def get_unread_count(self):
        """Get the number of unread messages for this participant"""
        if not self.last_read_at:
            return (
                self.chat.messages.filter(created_at__gte=self.joined_at)
                .exclude(sender=self.user)
                .count()
            )

        return (
            self.chat.messages.filter(created_at__gt=self.last_read_at)
            .exclude(sender=self.user)
            .count()
        )

    def is_muted(self):
        """Check if notifications are muted for this participant"""
        if not self.muted_until:
            return False
        return timezone.now() < self.muted_until

    def mute_notifications(self, duration_hours=24):
        """Mute notifications for a specified duration"""
        from datetime import timedelta

        self.muted_until = timezone.now() + timedelta(hours=duration_hours)
        self.save(update_fields=["muted_until"])

    def unmute_notifications(self):
        """Unmute notifications"""
        self.muted_until = None
        self.save(update_fields=["muted_until"])

    @property
    def display_name(self):
        """Get the display name for this participant"""
        return self.user.get_full_name() or self.user.email
