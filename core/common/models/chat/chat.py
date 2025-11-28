"""
Chat model for ClustR real-time communication system.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel


class ChatType(models.TextChoices):
    """Types of chat conversations"""

    DIRECT = "direct", _("Direct Message")
    GROUP = "group", _("Group Chat")
    ANNOUNCEMENT = "announcement", _("Announcement Chat")
    SUPPORT = "support", _("Support Chat")


class ChatStatus(models.TextChoices):
    """Status of chat conversations"""

    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")
    DISABLED = "disabled", _("Disabled")


class Chat(AbstractClusterModel):
    """
    Represents a chat conversation between users.
    Can be direct messages, group chats, or announcement channels.
    """

    name = models.CharField(
        max_length=255,
        verbose_name=_("Chat Name"),
        help_text=_("Display name for the chat (optional for direct messages)"),
        blank=True,
        null=True,
    )

    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Chat description or purpose"),
        blank=True,
        null=True,
    )

    chat_type = models.CharField(
        max_length=20,
        choices=ChatType.choices,
        default=ChatType.DIRECT,
        verbose_name=_("Chat Type"),
        help_text=_("Type of chat conversation"),
    )

    status = models.CharField(
        max_length=20,
        choices=ChatStatus.choices,
        default=ChatStatus.ACTIVE,
        verbose_name=_("Status"),
        help_text=_("Current status of the chat"),
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Is Public"),
        help_text=_("Whether this chat is public or private"),
    )

    is_moderated = models.BooleanField(
        default=False,
        verbose_name=_("Is Moderated"),
        help_text=_("Whether messages in this chat require moderation"),
    )

    max_participants = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Maximum Participants"),
        help_text=_("Maximum number of participants allowed in this chat"),
    )

    avatar = models.ImageField(
        upload_to="chat_avatars/",
        blank=True,
        null=True,
        verbose_name=_("Chat Avatar"),
        help_text=_("Avatar image for the chat"),
    )

    last_message_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last Message At"),
        help_text=_("Timestamp of the last message in this chat"),
    )

    message_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Message Count"),
        help_text=_("Total number of messages in this chat"),
    )

    class Meta:
        verbose_name = _("Chat")
        verbose_name_plural = _("Chats")
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["cluster", "chat_type"]),
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["last_message_at"]),
        ]

    def __str__(self):
        if self.name:
            return self.name
        elif self.chat_type == ChatType.DIRECT:
            participants = self.participants.filter(is_active=True)[:2]
            if participants.count() == 2:
                return f"{participants[0].user.get_full_name()} & {participants[1].user.get_full_name()}"
        return f"Chat {self.id}"

    @property
    def participant_count(self):
        """Get the number of active participants in this chat"""
        return self.participants.filter(is_active=True).count()

    def get_participants(self):
        """Get all active participants in this chat"""
        return self.participants.filter(is_active=True).select_related("user")

    def get_last_message(self):
        """Get the last message in this chat"""
        return self.messages.order_by("-created_at").first()

    def can_user_join(self, user):
        """Check if a user can join this chat"""
        if self.status != ChatStatus.ACTIVE:
            return False

        if self.participant_count >= self.max_participants:
            return False

        # Check if user is already a participant
        if self.participants.filter(user=user, is_active=True).exists():
            return False

        return True

    def increment_message_count(self):
        """Increment the message count for this chat"""
        self.message_count = models.F("message_count") + 1
        self.save(update_fields=["message_count"])

    def update_last_message_time(self):
        """Update the last message timestamp"""
        from django.utils import timezone

        self.last_message_at = timezone.now()
        self.save(update_fields=["last_message_at"])
