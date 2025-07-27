"""
Child security management models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from core.common.models.base import AbstractClusterModel
from core.common.code_generator import CodeGenerator


class Child(AbstractClusterModel):
    """
    Model for managing children/wards in the estate.
    """

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")

    name = models.CharField(
        verbose_name=_("child name"),
        max_length=100,
        help_text=_("Full name of the child"),
    )

    date_of_birth = models.DateField(
        verbose_name=_("date of birth"),
        help_text=_("Date of birth of the child"),
    )

    gender = models.CharField(
        verbose_name=_("gender"),
        max_length=10,
        choices=Gender.choices,
        help_text=_("Gender of the child"),
    )

    profile_photo = models.URLField(
        verbose_name=_("profile photo"),
        max_length=500,
        blank=True,
        null=True,
        help_text=_("URL to the child's profile photo"),
    )

    house_number = models.CharField(
        verbose_name=_("house number"),
        max_length=20,
        help_text=_("House/unit number where the child lives"),
    )

    parent = models.ForeignKey(
        verbose_name=_("parent/guardian"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="children",
        help_text=_("Parent or guardian of the child"),
    )

    emergency_contacts = models.JSONField(
        verbose_name=_("emergency contacts"),
        default=list,
        help_text=_("List of emergency contact information"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether the child is currently active in the system"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the child"),
    )

    class Meta:
        verbose_name = _("Child")
        verbose_name_plural = _("Children")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["cluster", "parent"]),
            models.Index(fields=["cluster", "is_active"]),
            models.Index(fields=["cluster", "house_number"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.parent.name})"

    @property
    def age(self):
        """Calculate the child's age in years"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def get_emergency_contacts_display(self):
        """Get formatted emergency contacts"""
        if not self.emergency_contacts:
            return []
        
        return [
            {
                'name': contact.get('name', ''),
                'phone': contact.get('phone', ''),
                'relationship': contact.get('relationship', ''),
            }
            for contact in self.emergency_contacts
        ]


class ExitRequest(AbstractClusterModel):
    """
    Model for managing child exit requests.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        DENIED = "denied", _("Denied")
        EXPIRED = "expired", _("Expired")

    request_id = models.CharField(
        verbose_name=_("request ID"),
        max_length=20,
        unique=True,
        help_text=_("Unique identifier for the exit request"),
    )

    child = models.ForeignKey(
        verbose_name=_("child"),
        to="common.Child",
        on_delete=models.CASCADE,
        related_name="exit_requests",
        help_text=_("The child this exit request is for"),
    )

    requested_by = models.ForeignKey(
        verbose_name=_("requested by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="child_exit_requests",
        help_text=_("User who requested the exit"),
    )

    reason = models.TextField(
        verbose_name=_("reason for exit"),
        help_text=_("Reason for the child's exit"),
    )

    expected_return_time = models.DateTimeField(
        verbose_name=_("expected return time"),
        help_text=_("Expected time for the child to return"),
    )

    destination = models.CharField(
        verbose_name=_("destination"),
        max_length=200,
        blank=True,
        help_text=_("Where the child is going"),
    )

    accompanying_adult = models.CharField(
        verbose_name=_("accompanying adult"),
        max_length=100,
        blank=True,
        help_text=_("Name of the adult accompanying the child"),
    )

    accompanying_adult_phone = models.CharField(
        verbose_name=_("accompanying adult phone"),
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=_(
                    "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
                ),
            )
        ],
        help_text=_("Phone number of the accompanying adult"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Current status of the exit request"),
    )

    approved_by = models.ForeignKey(
        verbose_name=_("approved by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="approved_exit_requests",
        null=True,
        blank=True,
        help_text=_("User who approved the exit request"),
    )

    approved_at = models.DateTimeField(
        verbose_name=_("approved at"),
        null=True,
        blank=True,
        help_text=_("When the exit request was approved"),
    )

    denied_by = models.ForeignKey(
        verbose_name=_("denied by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="denied_exit_requests",
        null=True,
        blank=True,
        help_text=_("User who denied the exit request"),
    )

    denied_at = models.DateTimeField(
        verbose_name=_("denied at"),
        null=True,
        blank=True,
        help_text=_("When the exit request was denied"),
    )

    denial_reason = models.TextField(
        verbose_name=_("denial reason"),
        blank=True,
        help_text=_("Reason for denying the exit request"),
    )

    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
        help_text=_("When the exit request expires"),
    )

    class Meta:
        verbose_name = _("Exit Request")
        verbose_name_plural = _("Exit Requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "child"]),
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "requested_by"]),
            models.Index(fields=["cluster", "created_at"]),
        ]

    def __str__(self):
        return f"Exit Request {self.request_id} for {self.child.name}"

    def save(self, *args, **kwargs):
        """Generate request ID if not provided"""
        if not self.request_id:
            self.request_id = f"EXIT-{CodeGenerator.generate_code(length=8, include_alpha=True).upper()}"
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the exit request has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_pending(self):
        """Check if the exit request is still pending"""
        return self.status == self.Status.PENDING and not self.is_expired

    def approve(self, user):
        """Approve the exit request"""
        from django.utils import timezone
        
        if self.status == self.Status.PENDING and not self.is_expired:
            self.status = self.Status.APPROVED
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save(update_fields=["status", "approved_by", "approved_at"])
            return True
        return False

    def deny(self, user, reason=""):
        """Deny the exit request"""
        from django.utils import timezone
        
        if self.status == self.Status.PENDING:
            self.status = self.Status.DENIED
            self.denied_by = user
            self.denied_at = timezone.now()
            self.denial_reason = reason
            self.save(update_fields=["status", "denied_by", "denied_at", "denial_reason"])
            return True
        return False


class EntryExitLog(AbstractClusterModel):
    """
    Model for tracking child entry and exit events.
    """

    class LogType(models.TextChoices):
        EXIT = "exit", _("Exit")
        ENTRY = "entry", _("Entry")

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        OVERDUE = "overdue", _("Overdue")

    child = models.ForeignKey(
        verbose_name=_("child"),
        to="common.Child",
        on_delete=models.CASCADE,
        related_name="entry_exit_logs",
        help_text=_("The child this log entry is for"),
    )

    exit_request = models.ForeignKey(
        verbose_name=_("exit request"),
        to="common.ExitRequest",
        on_delete=models.CASCADE,
        related_name="logs",
        null=True,
        blank=True,
        help_text=_("The exit request associated with this log"),
    )

    log_type = models.CharField(
        verbose_name=_("log type"),
        max_length=10,
        choices=LogType.choices,
        help_text=_("Type of log entry"),
    )

    date = models.DateField(
        verbose_name=_("date"),
        help_text=_("Date of the entry/exit"),
    )

    exit_time = models.TimeField(
        verbose_name=_("exit time"),
        null=True,
        blank=True,
        help_text=_("Time when the child exited"),
    )

    entry_time = models.TimeField(
        verbose_name=_("entry time"),
        null=True,
        blank=True,
        help_text=_("Time when the child returned"),
    )

    expected_return_time = models.DateTimeField(
        verbose_name=_("expected return time"),
        null=True,
        blank=True,
        help_text=_("Expected time for the child to return"),
    )

    actual_return_time = models.DateTimeField(
        verbose_name=_("actual return time"),
        null=True,
        blank=True,
        help_text=_("Actual time when the child returned"),
    )

    reason = models.TextField(
        verbose_name=_("reason"),
        help_text=_("Reason for the exit"),
    )

    destination = models.CharField(
        verbose_name=_("destination"),
        max_length=200,
        blank=True,
        help_text=_("Where the child went"),
    )

    accompanying_adult = models.CharField(
        verbose_name=_("accompanying adult"),
        max_length=100,
        blank=True,
        help_text=_("Name of the adult accompanying the child"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        help_text=_("Current status of the entry/exit"),
    )

    verified_by = models.ForeignKey(
        verbose_name=_("verified by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        related_name="verified_child_logs",
        null=True,
        blank=True,
        help_text=_("Security personnel who verified the exit/entry"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the entry/exit"),
    )

    class Meta:
        verbose_name = _("Entry/Exit Log")
        verbose_name_plural = _("Entry/Exit Logs")
        ordering = ["-date", "-exit_time"]
        indexes = [
            models.Index(fields=["cluster", "child"]),
            models.Index(fields=["cluster", "date"]),
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "log_type"]),
        ]

    def __str__(self):
        return f"{self.child.name} - {self.get_log_type_display()} on {self.date}"

    @property
    def is_overdue(self):
        """Check if the child is overdue for return"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.expected_return_time:
            return (
                self.status == self.Status.IN_PROGRESS and 
                timezone.now() > self.expected_return_time
            )
        return False

    @property
    def duration_minutes(self):
        """Calculate the duration of the exit in minutes"""
        if self.exit_time and self.entry_time:
            from datetime import datetime, timedelta
            
            # Combine date with times
            exit_datetime = datetime.combine(self.date, self.exit_time)
            
            # Handle case where entry is on the next day
            entry_date = self.date
            if self.entry_time < self.exit_time:
                entry_date = self.date + timedelta(days=1)
            
            entry_datetime = datetime.combine(entry_date, self.entry_time)
            
            return int((entry_datetime - exit_datetime).total_seconds() / 60)
        return None

    def mark_exit(self, verified_by=None):
        """Mark the child as having exited"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.status == self.Status.SCHEDULED:
            self.status = self.Status.IN_PROGRESS
            self.exit_time = timezone.now().time()
            if verified_by:
                self.verified_by = verified_by
            self.save(update_fields=["status", "exit_time", "verified_by"])
            return True
        return False

    def mark_entry(self, verified_by=None):
        """Mark the child as having returned"""
        from django.utils import timezone
        
        if self.log_type == self.LogType.EXIT and self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.COMPLETED
            self.entry_time = timezone.now().time()
            self.actual_return_time = timezone.now()
            if verified_by:
                self.verified_by = verified_by
            self.save(update_fields=["status", "entry_time", "actual_return_time", "verified_by"])
            return True
        return False

    def mark_overdue(self):
        """Mark the child as overdue"""
        if self.is_overdue and self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.OVERDUE
            self.save(update_fields=["status"])
            return True
        return False