"""
Meeting participant model for managing users in virtual meetings.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel


class ParticipantRole(models.TextChoices):
    """Roles for meeting participants"""

    HOST = "host", _("Host")
    CO_HOST = "co_host", _("Co-Host")
    MODERATOR = "moderator", _("Moderator")
    PARTICIPANT = "participant", _("Participant")
    OBSERVER = "observer", _("Observer")


class ParticipantStatus(models.TextChoices):
    """Status of meeting participants"""

    INVITED = "invited", _("Invited")
    CONFIRMED = "confirmed", _("Confirmed")
    DECLINED = "declined", _("Declined")
    JOINED = "joined", _("Joined")
    LEFT = "left", _("Left")
    REMOVED = "removed", _("Removed")


class MeetingParticipant(AbstractClusterModel):
    """
    Represents a user's participation in a meeting.
    Tracks invitation status, join/leave times, and permissions.
    """

    meeting = models.ForeignKey(
        "common.Meeting",
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name=_("Meeting"),
        help_text=_("The meeting this participant belongs to"),
    )

    user = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="meeting_participations",
        verbose_name=_("User"),
        help_text=_("The user participating in the meeting"),
    )

    role = models.CharField(
        max_length=20,
        choices=ParticipantRole.choices,
        default=ParticipantRole.PARTICIPANT,
        verbose_name=_("Role"),
        help_text=_("The role of the participant in this meeting"),
    )

    status = models.CharField(
        max_length=20,
        choices=ParticipantStatus.choices,
        default=ParticipantStatus.INVITED,
        verbose_name=_("Status"),
        help_text=_("Current status of the participant"),
    )

    invited_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Invited At"),
        help_text=_("When the participant was invited to the meeting"),
    )

    responded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Responded At"),
        help_text=_("When the participant responded to the invitation"),
    )

    joined_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Joined At"),
        help_text=_("When the participant joined the meeting"),
    )

    left_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Left At"),
        help_text=_("When the participant left the meeting"),
    )

    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Duration (Minutes)"),
        help_text=_("Total time spent in the meeting in minutes"),
    )

    can_share_screen = models.BooleanField(
        default=True,
        verbose_name=_("Can Share Screen"),
        help_text=_("Whether the participant can share their screen"),
    )

    can_use_microphone = models.BooleanField(
        default=True,
        verbose_name=_("Can Use Microphone"),
        help_text=_("Whether the participant can use their microphone"),
    )

    can_use_camera = models.BooleanField(
        default=True,
        verbose_name=_("Can Use Camera"),
        help_text=_("Whether the participant can use their camera"),
    )

    can_use_chat = models.BooleanField(
        default=True,
        verbose_name=_("Can Use Chat"),
        help_text=_("Whether the participant can use the meeting chat"),
    )

    is_muted = models.BooleanField(
        default=False,
        verbose_name=_("Is Muted"),
        help_text=_("Whether the participant's microphone is muted"),
    )

    camera_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Camera Enabled"),
        help_text=_("Whether the participant's camera is enabled"),
    )

    connection_quality = models.CharField(
        max_length=20,
        choices=[
            ("excellent", _("Excellent")),
            ("good", _("Good")),
            ("fair", _("Fair")),
            ("poor", _("Poor")),
            ("unknown", _("Unknown")),
        ],
        default="unknown",
        verbose_name=_("Connection Quality"),
        help_text=_("Quality of the participant's connection"),
    )

    device_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Device Info"),
        help_text=_("Information about the participant's device"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Additional notes about the participant"),
    )

    class Meta:
        verbose_name = _("Meeting Participant")
        verbose_name_plural = _("Meeting Participants")
        unique_together = ["meeting", "user"]
        ordering = ["-invited_at"]
        indexes = [
            models.Index(fields=["meeting", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["role"]),
            models.Index(fields=["joined_at"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.meeting.title}"

    def confirm_attendance(self):
        """Confirm attendance to the meeting"""
        self.status = ParticipantStatus.CONFIRMED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def decline_attendance(self):
        """Decline attendance to the meeting"""
        self.status = ParticipantStatus.DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def join_meeting(self):
        """Mark participant as joined"""
        self.status = ParticipantStatus.JOINED
        self.joined_at = timezone.now()
        self.save(update_fields=["status", "joined_at"])

    def leave_meeting(self):
        """Mark participant as left and calculate duration"""
        self.status = ParticipantStatus.LEFT
        self.left_at = timezone.now()

        if self.joined_at:
            duration = self.left_at - self.joined_at
            self.duration_minutes = int(duration.total_seconds() / 60)

        self.save(update_fields=["status", "left_at", "duration_minutes"])

    def remove_from_meeting(self, reason=None):
        """Remove participant from meeting"""
        self.status = ParticipantStatus.REMOVED
        self.left_at = timezone.now()

        if reason:
            self.notes = f"Removed: {reason}"

        if self.joined_at:
            duration = self.left_at - self.joined_at
            self.duration_minutes = int(duration.total_seconds() / 60)

        self.save(update_fields=["status", "left_at", "duration_minutes", "notes"])

    def mute_participant(self):
        """Mute the participant's microphone"""
        self.is_muted = True
        self.save(update_fields=["is_muted"])

    def unmute_participant(self):
        """Unmute the participant's microphone"""
        self.is_muted = False
        self.save(update_fields=["is_muted"])

    def enable_camera(self):
        """Enable the participant's camera"""
        self.camera_enabled = True
        self.save(update_fields=["camera_enabled"])

    def disable_camera(self):
        """Disable the participant's camera"""
        self.camera_enabled = False
        self.save(update_fields=["camera_enabled"])

    def update_connection_quality(self, quality):
        """Update the participant's connection quality"""
        self.connection_quality = quality
        self.save(update_fields=["connection_quality"])

    def promote_to_host(self):
        """Promote participant to host role"""
        self.role = ParticipantRole.HOST
        self.can_share_screen = True
        self.can_use_microphone = True
        self.can_use_camera = True
        self.can_use_chat = True
        self.save(
            update_fields=[
                "role",
                "can_share_screen",
                "can_use_microphone",
                "can_use_camera",
                "can_use_chat",
            ]
        )

    def promote_to_moderator(self):
        """Promote participant to moderator role"""
        self.role = ParticipantRole.MODERATOR
        self.save(update_fields=["role"])

    def demote_to_participant(self):
        """Demote participant to regular participant role"""
        self.role = ParticipantRole.PARTICIPANT
        self.save(update_fields=["role"])

    @property
    def display_name(self):
        """Get the display name for this participant"""
        return self.user.get_full_name() or self.user.email

    @property
    def is_host(self):
        """Check if the participant is a host"""
        return self.role in [ParticipantRole.HOST, ParticipantRole.CO_HOST]

    @property
    def can_moderate(self):
        """Check if the participant can moderate the meeting"""
        return self.role in [
            ParticipantRole.HOST,
            ParticipantRole.CO_HOST,
            ParticipantRole.MODERATOR,
        ]

    @property
    def attendance_percentage(self):
        """Calculate attendance percentage based on meeting duration"""
        if not self.meeting.actual_duration_minutes or self.duration_minutes == 0:
            return 0

        return min(
            100, (self.duration_minutes / self.meeting.actual_duration_minutes) * 100
        )
