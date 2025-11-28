"""
Meeting recording model for storing meeting recordings.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

from core.common.models.base import AbstractClusterModel


class RecordingType(models.TextChoices):
    """Types of meeting recordings"""

    FULL = "full", _("Full Meeting Recording")
    AUDIO_ONLY = "audio_only", _("Audio Only")
    SCREEN_SHARE = "screen_share", _("Screen Share Only")
    HIGHLIGHTS = "highlights", _("Meeting Highlights")


class RecordingStatus(models.TextChoices):
    """Status of meeting recordings"""

    RECORDING = "recording", _("Recording")
    PROCESSING = "processing", _("Processing")
    READY = "ready", _("Ready")
    FAILED = "failed", _("Failed")
    ARCHIVED = "archived", _("Archived")
    DELETED = "deleted", _("Deleted")


class MeetingRecording(AbstractClusterModel):
    """
    Represents a recording of a meeting.
    Supports different recording types and processing states.
    """

    meeting = models.ForeignKey(
        "common.Meeting",
        on_delete=models.CASCADE,
        related_name="recordings",
        verbose_name=_("Meeting"),
        help_text=_("The meeting this recording belongs to"),
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("Recording Title"),
        help_text=_("Title of the recording"),
    )

    recording_type = models.CharField(
        max_length=20,
        choices=RecordingType.choices,
        default=RecordingType.FULL,
        verbose_name=_("Recording Type"),
        help_text=_("Type of recording"),
    )

    status = models.CharField(
        max_length=20,
        choices=RecordingStatus.choices,
        default=RecordingStatus.RECORDING,
        verbose_name=_("Status"),
        help_text=_("Current status of the recording"),
    )

    file = models.FileField(
        upload_to="meeting_recordings/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Recording File"),
        help_text=_("The recording file"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "mp4",
                    "avi",
                    "mov",
                    "wmv",
                    "flv",
                    "webm",
                    "mp3",
                    "wav",
                    "ogg",
                ]
            )
        ],
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
        verbose_name=_("File Size"),
        help_text=_("Size of the recording file in bytes"),
    )

    duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Duration (Seconds)"),
        help_text=_("Duration of the recording in seconds"),
    )

    start_time = models.DateTimeField(
        verbose_name=_("Recording Start Time"),
        help_text=_("When the recording started"),
    )

    end_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Recording End Time"),
        help_text=_("When the recording ended"),
    )

    thumbnail = models.ImageField(
        upload_to="meeting_thumbnails/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Thumbnail"),
        help_text=_("Thumbnail image for the recording"),
    )

    transcript = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Transcript"),
        help_text=_("Auto-generated transcript of the recording"),
    )

    external_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("External URL"),
        help_text=_("URL to external recording service"),
    )

    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("External ID"),
        help_text=_("ID from external recording service"),
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Is Public"),
        help_text=_("Whether this recording is publicly accessible"),
    )

    requires_authentication = models.BooleanField(
        default=True,
        verbose_name=_("Requires Authentication"),
        help_text=_("Whether viewing requires authentication"),
    )

    download_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Download Enabled"),
        help_text=_("Whether the recording can be downloaded"),
    )

    auto_delete_after_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Auto Delete After Days"),
        help_text=_("Number of days after which to auto-delete the recording"),
    )

    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("View Count"),
        help_text=_("Number of times the recording has been viewed"),
    )

    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Download Count"),
        help_text=_("Number of times the recording has been downloaded"),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional metadata about the recording"),
    )

    processing_error = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Processing Error"),
        help_text=_("Error message if processing failed"),
    )

    class Meta:
        verbose_name = _("Meeting Recording")
        verbose_name_plural = _("Meeting Recordings")
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["meeting", "status"]),
            models.Index(fields=["status", "start_time"]),
            models.Index(fields=["recording_type"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.meeting.title}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.meeting.title} Recording"

        if self.file and not self.file_size:
            self.file_size = self.file.size

        super().save(*args, **kwargs)

    def start_recording(self):
        """Start the recording"""
        from django.utils import timezone

        self.status = RecordingStatus.RECORDING
        self.start_time = timezone.now()
        self.save(update_fields=["status", "start_time"])

    def stop_recording(self):
        """Stop the recording and begin processing"""
        from django.utils import timezone

        self.status = RecordingStatus.PROCESSING
        self.end_time = timezone.now()

        if self.start_time:
            duration = self.end_time - self.start_time
            self.duration_seconds = int(duration.total_seconds())

        self.save(update_fields=["status", "end_time", "duration_seconds"])

    def mark_ready(self):
        """Mark the recording as ready for viewing"""
        self.status = RecordingStatus.READY
        self.save(update_fields=["status"])

    def mark_failed(self, error_message=None):
        """Mark the recording as failed"""
        self.status = RecordingStatus.FAILED
        if error_message:
            self.processing_error = error_message
        self.save(update_fields=["status", "processing_error"])

    def archive_recording(self):
        """Archive the recording"""
        self.status = RecordingStatus.ARCHIVED
        self.save(update_fields=["status"])

    def soft_delete(self):
        """Soft delete the recording"""
        self.status = RecordingStatus.DELETED
        self.save(update_fields=["status"])

    def increment_view_count(self):
        """Increment the view count"""
        self.view_count = models.F("view_count") + 1
        self.save(update_fields=["view_count"])

    def increment_download_count(self):
        """Increment the download count"""
        self.download_count = models.F("download_count") + 1
        self.save(update_fields=["download_count"])

    @property
    def duration_formatted(self):
        """Get formatted duration string"""
        if not self.duration_seconds:
            return "0:00"

        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @property
    def file_size_human(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "0 B"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def is_available(self):
        """Check if the recording is available for viewing"""
        return self.status == RecordingStatus.READY and not self.is_expired

    @property
    def is_expired(self):
        """Check if the recording has expired"""
        if not self.auto_delete_after_days:
            return False

        from django.utils import timezone
        from datetime import timedelta

        expiry_date = self.created_at + timedelta(days=self.auto_delete_after_days)
        return timezone.now() > expiry_date

    def get_playback_url(self):
        """Get the URL for playing back the recording"""
        if self.external_url:
            return self.external_url
        elif self.file:
            return self.file.url
        return None

    def can_user_access(self, user):
        """Check if a user can access this recording"""
        if not self.is_available:
            return False

        if self.is_public and not self.requires_authentication:
            return True

        if not user or not user.is_authenticated:
            return False

        # Check if user was a participant in the meeting
        if self.meeting.participants.filter(user=user).exists():
            return True

        # Check if user is the meeting organizer
        if self.meeting.organizer == user:
            return True

        return False
