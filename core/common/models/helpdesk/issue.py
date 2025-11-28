"""
Issue models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.code_generator import CodeGenerator

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')

def generate_issue_number():
    """Generate a unique issue number"""
    return f"ISS-{CodeGenerator.generate_code(length=6, include_alpha=True).upper()}"


class IssuePriority(models.TextChoices):
    """Issue priority choices"""
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")

class IssueStatus(models.TextChoices):
    """Issue status choices"""
    SUBMITTED = "SUBMITTED", _("Submitted")
    OPEN = "OPEN", _("Open")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    PENDING = "PENDING", _("Pending")
    RESOLVED = "RESOLVED", _("Resolved")
    CLOSED = "CLOSED", _("Closed")


class IssueType(models.TextChoices):
    """Issue type choices"""
    CARPENTRY = "CARPENTRY", _("Carpentry")
    PLUMBING = "PLUMBING", _("Plumbing")
    ELECTRICAL = "ELECTRICAL", _("Electrical")
    CLEANING = "CLEANING", _("Cleaning")
    SECURITY = "SECURITY", _("Security")
    OTHER = "OTHER", _("Other")


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
        default_permissions = []
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
        default_permissions = []
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
        if self.pk and not self._state.adding:
            old_instance = IssueTicket.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == IssueStatus.RESOLVED and not self.resolved_at:
                    self.resolved_at = timezone.now()
                elif self.status == IssueStatus.CLOSED and not self.closed_at:
                    self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)

    @transaction.atomic()
    def assign(self, assign_to):
        if not assign_to:
            return Response(
                {'error': 'assigned_to is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
                
        old_assigned_to = issue.assigned_to
        issue.assigned_to = assigned_to
        issue.save(update_fields=["assigned_to"])
        
        def _on_commit():
            # Send notification
            if old_assigned_to != assigned_to:
                from core.common.includes import notifications
                from core.notifications.events import NotificationEvents
                
                notifications.send(
                    event=NotificationEvents.ISSUE_ASSIGNED,
                    recipients=[assigned_to],
                    cluster=issue.cluster,
                    context={
                        'issue_number': issue.issue_number,
                        'title': issue.title,
                        'description': issue.description[:200] + '...' if len(issue.description) > 200 else issue.description,
                        'priority': issue.get_priority_display(),
                        'category': issue.get_category_display(),
                        'location': issue.location or 'Not specified',
                        'assigned_to_name': assigned_to.name,
                        'reported_by_name': issue.reported_by.name if issue.reported_by else 'System',
                    }
                )
        
        transaction.on_commit(_on_commit)


    def escalate(escalate_to):
        if issue.escalated_at:
            return Response(
                {'error': 'Issue is already escalated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        issue.escalated_at = timezone.now()
        issue.priority = IssuePriority.URGENT
        issue.save()
        
        notifications.send(
            event=NotificationEvents.ISSUE_ESCALATED,
            recipients=[issue.assigned_to, issue.reported_by], # Assuming both assigned_to and reported_by should be notified
            cluster=issue.cluster,
            context={
                "issue_number": issue.issue_no,
                "issue_title": issue.title,
                "issue_description": issue.description,
                "issue_type": issue.get_issue_type_display(),
                "priority": issue.get_priority_display(),
                "reported_by_name": issue.reported_by.name,
                "escalated_at": issue.escalated_at.strftime('%Y-%m-%d %H:%M'),
            }
        )
