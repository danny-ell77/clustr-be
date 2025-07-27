"""
Help desk models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel
from core.common.code_generator import CodeGenerator


class IssueType(models.TextChoices):
    """Issue type choices"""
    CARPENTRY = "CARPENTRY", _("Carpentry")
    PLUMBING = "PLUMBING", _("Plumbing")
    ELECTRICAL = "ELECTRICAL", _("Electrical")
    CLEANING = "CLEANING", _("Cleaning")
    SECURITY = "SECURITY", _("Security")
    OTHER = "OTHER", _("Other")


class IssueStatus(models.TextChoices):
    """Issue status choices"""
    SUBMITTED = "SUBMITTED", _("Submitted")
    OPEN = "OPEN", _("Open")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    PENDING = "PENDING", _("Pending")
    RESOLVED = "RESOLVED", _("Resolved")
    CLOSED = "CLOSED", _("Closed")


class IssuePriority(models.TextChoices):
    """Issue priority choices"""
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


def generate_issue_number():
    """Generate a unique issue number"""
    return f"ISS-{CodeGenerator.generate_code(length=6, include_alpha=True).upper()}"


class IssueTicket(AbstractClusterModel):
    """
    Model for help desk issue tickets.
    """
    
    issue_no = models.CharField(
        verbose_name=_("issue number"),
        max_length=20,
        unique=True,
        default=generate_issue_number,
        help_text=_("Unique issue number for tracking"),
    )
    
    issue_type = models.CharField(
        verbose_name=_("issue type"),
        max_length=20,
        choices=IssueType.choices,
        default=IssueType.OTHER,
        help_text=_("Type of issue being reported"),
    )
    
    title = models.CharField(
        verbose_name=_("title"),
        max_length=200,
        help_text=_("Brief title describing the issue"),
    )
    
    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Detailed description of the issue"),
    )
    
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.SUBMITTED,
        help_text=_("Current status of the issue"),
    )
    
    priority = models.CharField(
        verbose_name=_("priority"),
        max_length=10,
        choices=IssuePriority.choices,
        default=IssuePriority.MEDIUM,
        help_text=_("Priority level of the issue"),
    )
    
    reported_by = models.ForeignKey(
        verbose_name=_("reported by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="reported_issues",
        help_text=_("User who reported the issue"),
    )
    
    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
        help_text=_("Staff member assigned to handle the issue"),
    )
    
    resolved_at = models.DateTimeField(
        verbose_name=_("resolved at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the issue was resolved"),
    )
    
    closed_at = models.DateTimeField(
        verbose_name=_("closed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the issue was closed"),
    )
    
    escalated_at = models.DateTimeField(
        verbose_name=_("escalated at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the issue was escalated"),
    )
    
    due_date = models.DateTimeField(
        verbose_name=_("due date"),
        null=True,
        blank=True,
        help_text=_("Expected resolution date"),
    )
    
    resolution_notes = models.TextField(
        verbose_name=_("resolution notes"),
        blank=True,
        help_text=_("Notes about how the issue was resolved"),
    )

    class Meta:
        verbose_name = _("issue ticket")
        verbose_name_plural = _("issue tickets")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["issue_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["issue_type"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["reported_by"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.issue_no} - {self.title}"

    @property
    def comments_count(self):
        """Get the number of comments on this issue"""
        return self.comments.count()

    def save(self, *args, **kwargs):
        """Override save to handle status changes"""
        from django.utils import timezone
        
        # Track status changes
        if self.pk:
            old_instance = IssueTicket.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == IssueStatus.RESOLVED and not self.resolved_at:
                    self.resolved_at = timezone.now()
                elif self.status == IssueStatus.CLOSED and not self.closed_at:
                    self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)


class IssueComment(AbstractClusterModel):
    """
    Model for comments on issue tickets.
    """
    
    issue = models.ForeignKey(
        verbose_name=_("issue"),
        to="common.IssueTicket",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text=_("The issue this comment belongs to"),
    )
    
    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="issue_comments",
        help_text=_("User who wrote the comment"),
    )
    
    content = models.TextField(
        verbose_name=_("content"),
        help_text=_("Content of the comment"),
    )
    
    is_internal = models.BooleanField(
        verbose_name=_("is internal"),
        default=False,
        help_text=_("Whether this comment is internal (staff only)"),
    )
    
    parent = models.ForeignKey(
        verbose_name=_("parent comment"),
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text=_("Parent comment for threaded discussions"),
    )

    class Meta:
        verbose_name = _("issue comment")
        verbose_name_plural = _("issue comments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["author"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_internal"]),
        ]

    def __str__(self):
        return f"Comment on {self.issue.issue_no} by {self.author.name}"


class IssueAttachment(AbstractClusterModel):
    """
    Model for file attachments on issue tickets and comments.
    """
    
    issue = models.ForeignKey(
        verbose_name=_("issue"),
        to="common.IssueTicket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        help_text=_("The issue this attachment belongs to"),
    )
    
    comment = models.ForeignKey(
        verbose_name=_("comment"),
        to="common.IssueComment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        help_text=_("The comment this attachment belongs to"),
    )
    
    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file"),
    )
    
    file_url = models.URLField(
        verbose_name=_("file URL"),
        help_text=_("URL to access the uploaded file"),
    )
    
    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"),
        help_text=_("Size of the file in bytes"),
    )
    
    file_type = models.CharField(
        verbose_name=_("file type"),
        max_length=100,
        help_text=_("MIME type of the file"),
    )
    
    uploaded_by = models.ForeignKey(
        verbose_name=_("uploaded by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="issue_attachments",
        help_text=_("User who uploaded the file"),
    )

    class Meta:
        verbose_name = _("issue attachment")
        verbose_name_plural = _("issue attachments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["comment"]),
            models.Index(fields=["uploaded_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(issue__isnull=False) | models.Q(comment__isnull=False),
                name="attachment_belongs_to_issue_or_comment"
            )
        ]

    def __str__(self):
        if self.issue:
            return f"Attachment for {self.issue.issue_no}: {self.file_name}"
        elif self.comment:
            return f"Attachment for comment on {self.comment.issue.issue_no}: {self.file_name}"
        return f"Attachment: {self.file_name}"


class IssueStatusHistory(AbstractClusterModel):
    """
    Model to track status changes for issue tickets.
    """
    
    issue = models.ForeignKey(
        verbose_name=_("issue"),
        to="common.IssueTicket",
        on_delete=models.CASCADE,
        related_name="status_history",
        help_text=_("The issue this status change belongs to"),
    )
    
    from_status = models.CharField(
        verbose_name=_("from status"),
        max_length=20,
        choices=IssueStatus.choices,
        null=True,
        blank=True,
        help_text=_("Previous status"),
    )
    
    to_status = models.CharField(
        verbose_name=_("to status"),
        max_length=20,
        choices=IssueStatus.choices,
        help_text=_("New status"),
    )
    
    changed_by = models.ForeignKey(
        verbose_name=_("changed by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="issue_status_changes",
        help_text=_("User who changed the status"),
    )
    
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Notes about the status change"),
    )

    class Meta:
        verbose_name = _("issue status history")
        verbose_name_plural = _("issue status histories")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["to_status"]),
            models.Index(fields=["changed_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.issue.issue_no}: {self.from_status} → {self.to_status}"