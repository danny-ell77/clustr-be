"""
Message and message-related models for ClustR chat system.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

from core.common.models.base import AbstractClusterModel


class MessageType(models.TextChoices):
    """Types of messages"""

    TEXT = "text", _("Text Message")
    IMAGE = "image", _("Image")
    FILE = "file", _("File")
    AUDIO = "audio", _("Audio")
    VIDEO = "video", _("Video")
    LOCATION = "location", _("Location")
    SYSTEM = "system", _("System Message")
    ANNOUNCEMENT = "announcement", _("Announcement")


class MessageStatus(models.TextChoices):
    """Status of messages"""

    SENT = "sent", _("Sent")
    DELIVERED = "delivered", _("Delivered")
    READ = "read", _("Read")
    FAILED = "failed", _("Failed")
    PENDING = "pending", _("Pending")
    MODERATED = "moderated", _("Under Moderation")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class Message(AbstractClusterModel):
    """
    Represents a message in a chat conversation.
    Supports text, media, and system messages.
    """

    chat = models.ForeignKey(
        "common.Chat",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Chat"),
        help_text=_("The chat this message belongs to"),
    )

    sender = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name=_("Sender"),
        help_text=_("The user who sent this message"),
        null=True,
        blank=True,  # Allow null for system messages
    )

    content = models.TextField(
        verbose_name=_("Content"), help_text=_("The message content"), blank=True
    )

    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name=_("Message Type"),
        help_text=_("Type of message content"),
    )

    status = models.CharField(
        max_length=20,
        choices=MessageStatus.choices,
        default=MessageStatus.SENT,
        verbose_name=_("Status"),
        help_text=_("Current status of the message"),
    )

    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="replies",
        verbose_name=_("Reply To"),
        help_text=_("The message this is a reply to"),
    )

    is_edited = models.BooleanField(
        default=False,
        verbose_name=_("Is Edited"),
        help_text=_("Whether this message has been edited"),
    )

    edited_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Edited At"),
        help_text=_("When the message was last edited"),
    )

    is_pinned = models.BooleanField(
        default=False,
        verbose_name=_("Is Pinned"),
        help_text=_("Whether this message is pinned in the chat"),
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_("Is Deleted"),
        help_text=_("Whether this message has been deleted"),
    )

    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Deleted At"),
        help_text=_("When the message was deleted"),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional metadata for the message (location, file info, etc.)"),
    )

    moderation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Moderation Reason"),
        help_text=_("Reason for moderation action"),
    )

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["chat", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["message_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_deleted", "created_at"]),
        ]

    def __str__(self):
        sender_name = self.sender.get_full_name() if self.sender else "System"
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return f"{sender_name}: {content_preview}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Update chat's last message time and message count for new messages
        if is_new and not self.is_deleted:
            self.chat.update_last_message_time()
            self.chat.increment_message_count()

    def soft_delete(self, reason=None):
        """Soft delete the message"""
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        if reason:
            self.moderation_reason = reason
        self.save(update_fields=["is_deleted", "deleted_at", "moderation_reason"])

    def edit_content(self, new_content):
        """Edit the message content"""
        from django.utils import timezone

        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=["content", "is_edited", "edited_at"])

    def pin_message(self):
        """Pin the message in the chat"""
        self.is_pinned = True
        self.save(update_fields=["is_pinned"])

    def unpin_message(self):
        """Unpin the message in the chat"""
        self.is_pinned = False
        self.save(update_fields=["is_pinned"])

    def approve_message(self):
        """Approve a moderated message"""
        self.status = MessageStatus.APPROVED
        self.save(update_fields=["status"])

    def reject_message(self, reason=None):
        """Reject a moderated message"""
        self.status = MessageStatus.REJECTED
        if reason:
            self.moderation_reason = reason
        self.save(update_fields=["status", "moderation_reason"])

    @property
    def can_be_edited(self):
        """Check if the message can be edited"""
        if self.is_deleted or self.message_type != MessageType.TEXT:
            return False

        # Allow editing within 24 hours
        from django.utils import timezone
        from datetime import timedelta

        edit_window = timezone.now() - timedelta(hours=24)
        return self.created_at > edit_window

    @property
    def reply_count(self):
        """Get the number of replies to this message"""
        return self.replies.filter(is_deleted=False).count()


class MessageAttachment(AbstractClusterModel):
    """
    Represents file attachments for messages.
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Message"),
        help_text=_("The message this attachment belongs to"),
    )

    file = models.FileField(
        upload_to="chat_attachments/%Y/%m/%d/",
        verbose_name=_("File"),
        help_text=_("The attached file"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "doc",
                    "docx",
                    "txt",
                    "rtf",  # Documents
                    "jpg",
                    "jpeg",
                    "png",
                    "gif",
                    "bmp",
                    "webp",  # Images
                    "mp4",
                    "avi",
                    "mov",
                    "wmv",
                    "flv",
                    "webm",  # Videos
                    "mp3",
                    "wav",
                    "ogg",
                    "aac",
                    "m4a",  # Audio
                    "zip",
                    "rar",
                    "7z",
                    "tar",
                    "gz",  # Archives
                    "xls",
                    "xlsx",
                    "csv",  # Spreadsheets
                    "ppt",
                    "pptx",  # Presentations
                ]
            )
        ],
    )

    original_filename = models.CharField(
        max_length=255,
        verbose_name=_("Original Filename"),
        help_text=_("The original name of the uploaded file"),
    )

    file_size = models.PositiveIntegerField(
        verbose_name=_("File Size"), help_text=_("Size of the file in bytes")
    )

    mime_type = models.CharField(
        max_length=100,
        verbose_name=_("MIME Type"),
        help_text=_("MIME type of the file"),
    )

    thumbnail = models.ImageField(
        upload_to="chat_thumbnails/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Thumbnail"),
        help_text=_("Thumbnail image for the attachment"),
    )

    class Meta:
        verbose_name = _("Message Attachment")
        verbose_name_plural = _("Message Attachments")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attachment: {self.original_filename}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.original_filename = self.file.name

            # Set MIME type based on file extension
            import mimetypes

            self.mime_type, _ = mimetypes.guess_type(self.file.name)
            if not self.mime_type:
                self.mime_type = "application/octet-stream"

        super().save(*args, **kwargs)

    @property
    def is_image(self):
        """Check if the attachment is an image"""
        return self.mime_type and self.mime_type.startswith("image/")

    @property
    def is_video(self):
        """Check if the attachment is a video"""
        return self.mime_type and self.mime_type.startswith("video/")

    @property
    def is_audio(self):
        """Check if the attachment is audio"""
        return self.mime_type and self.mime_type.startswith("audio/")

    @property
    def file_size_human(self):
        """Get human-readable file size"""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
