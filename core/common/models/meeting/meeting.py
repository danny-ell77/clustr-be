"""
Meeting model for ClustR virtual meeting system.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel


class MeetingType(models.TextChoices):
    """Types of meetings"""

    COMMUNITY = "community", _("Community Meeting")
    COMMITTEE = "committee", _("Committee Meeting")
    EMERGENCY = "emergency", _("Emergency Meeting")
    BOARD = "board", _("Board Meeting")
    GENERAL = "general", _("General Meeting")
    TRAINING = "training", _("Training Session")
    SOCIAL = "social", _("Social Event")


class MeetingStatus(models.TextChoices):
    """Status of meetings"""

    SCHEDULED = "scheduled", _("Scheduled")
    LIVE = "live", _("Live")
    ENDED = "ended", _("Ended")
    CANCELLED = "cancelled", _("Cancelled")
    POSTPONED = "postponed", _("Postponed")


class Meeting(AbstractClusterModel):
    """
    Represents a virtual meeting in the ClustR system.
    Supports scheduling, participant management, and basic recording.
    """

    title = models.CharField(
        max_length=255,
        verbose_name=_("Meeting Title"),
        help_text=_("The title of the meeting"),
    )

    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the meeting"),
        blank=True,
    )

    meeting_type = models.CharField(
        max_length=20,
        choices=MeetingType.choices,
        default=MeetingType.GENERAL,
        verbose_name=_("Meeting Type"),
        help_text=_("Type of meeting"),
    )

    status = models.CharField(
        max_length=20,
        choices=MeetingStatus.choices,
        default=MeetingStatus.SCHEDULED,
        verbose_name=_("Status"),
        help_text=_("Current status of the meeting"),
    )

    organizer = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="organized_meetings",
        verbose_name=_("Organizer"),
        help_text=_("The user who organized this meeting"),
    )

    scheduled_start = models.DateTimeField(
        verbose_name=_("Scheduled Start Time"),
        help_text=_("When the meeting is scheduled to start"),
    )

    scheduled_end = models.DateTimeField(
        verbose_name=_("Scheduled End Time"),
        help_text=_("When the meeting is scheduled to end"),
    )

    actual_start = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Actual Start Time"),
        help_text=_("When the meeting actually started"),
    )

    actual_end = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Actual End Time"),
        help_text=_("When the meeting actually ended"),
    )

    meeting_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Meeting URL"),
        help_text=_("URL to join the meeting (external platform)"),
    )

    meeting_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Meeting ID"),
        help_text=_("External meeting platform ID"),
    )

    passcode = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Meeting Passcode"),
        help_text=_("Passcode required to join the meeting"),
    )

    max_participants = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Maximum Participants"),
        help_text=_("Maximum number of participants allowed"),
    )

    is_recording_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Recording Enabled"),
        help_text=_("Whether recording is enabled for this meeting"),
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Is Public"),
        help_text=_("Whether this meeting is open to all cluster members"),
    )

    requires_approval = models.BooleanField(
        default=False,
        verbose_name=_("Requires Approval"),
        help_text=_("Whether participants need approval to join"),
    )

    agenda = models.TextField(
        blank=True,
        verbose_name=_("Agenda"),
        help_text=_("Meeting agenda and topics to be discussed"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Meeting Notes"),
        help_text=_("Notes taken during the meeting"),
    )

    attachments = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Attachments"),
        help_text=_("List of file attachments for the meeting"),
    )

    reminder_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Reminder Settings"),
        help_text=_("Settings for meeting reminders"),
    )

    platform_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Platform Data"),
        help_text=_("Additional data from external meeting platforms"),
    )

    class Meta:
        verbose_name = _("Meeting")
        verbose_name_plural = _("Meetings")
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["cluster", "scheduled_start"]),
            models.Index(fields=["organizer", "scheduled_start"]),
            models.Index(fields=["status", "scheduled_start"]),
            models.Index(fields=["meeting_type"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.scheduled_start.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration_minutes(self):
        """Get the scheduled duration in minutes"""
        if self.scheduled_end and self.scheduled_start:
            delta = self.scheduled_end - self.scheduled_start
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def actual_duration_minutes(self):
        """Get the actual duration in minutes"""
        if self.actual_end and self.actual_start:
            delta = self.actual_end - self.actual_start
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def participant_count(self):
        """Get the number of participants"""
        return self.participants.filter(status__in=["confirmed", "joined"]).count()

    @property
    def is_upcoming(self):
        """Check if the meeting is upcoming"""
        return (
            self.scheduled_start > timezone.now()
            and self.status == MeetingStatus.SCHEDULED
        )

    @property
    def is_ongoing(self):
        """Check if the meeting is currently ongoing"""
        return self.status == MeetingStatus.LIVE

    @property
    def has_ended(self):
        """Check if the meeting has ended"""
        return self.status == MeetingStatus.ENDED

    def start_meeting(self):
        """Start the meeting"""
        self.status = MeetingStatus.LIVE
        self.actual_start = timezone.now()
        self.save(update_fields=["status", "actual_start"])

    def end_meeting(self):
        """End the meeting"""
        self.status = MeetingStatus.ENDED
        self.actual_end = timezone.now()
        self.save(update_fields=["status", "actual_end"])

    def cancel_meeting(self, reason=None):
        """Cancel the meeting"""
        self.status = MeetingStatus.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}"
        self.save(update_fields=["status", "notes"])

    def postpone_meeting(self, new_start_time, new_end_time=None):
        """Postpone the meeting to a new time"""
        self.status = MeetingStatus.POSTPONED
        self.scheduled_start = new_start_time
        if new_end_time:
            self.scheduled_end = new_end_time
        self.save(update_fields=["status", "scheduled_start", "scheduled_end"])

    def can_user_join(self, user):
        """Check if a user can join this meeting"""
        if self.status not in [MeetingStatus.SCHEDULED, MeetingStatus.LIVE]:
            return False

        if not self.is_public:
            # Check if user is a participant
            if not self.participants.filter(user=user).exists():
                return False

        if self.participant_count >= self.max_participants:
            return False

        return True

    def get_join_url(self):
        """Get the URL to join the meeting"""
        if self.meeting_url:
            return self.meeting_url

        # Return internal meeting room URL
        return f"/meetings/{self.id}/join/"

    def send_reminders(self):
        """Send meeting reminders to participants"""
        # Implementation would depend on notification system
        pass

    def generate_meeting_summary(self):
        """Generate a summary of the meeting"""
        summary = {
            "title": self.title,
            "duration": self.actual_duration_minutes,
            "participants": self.participant_count,
            "recordings": self.recordings.count(),
            "notes": self.notes,
        }
        return summary
