"""
Task management models for ClustR application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

from core.common.models.base import AbstractClusterModel
from core.common.code_generator import CodeGenerator


class TaskType(models.TextChoices):
    """Types of tasks available."""
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    SECURITY = "SECURITY", _("Security")
    CLEANING = "CLEANING", _("Cleaning")
    ADMINISTRATIVE = "ADMINISTRATIVE", _("Administrative")
    INSPECTION = "INSPECTION", _("Inspection")
    REPAIR = "REPAIR", _("Repair")
    OTHER = "OTHER", _("Other")


class TaskStatus(models.TextChoices):
    """Status of a task."""
    PENDING = "PENDING", _("Pending")
    ASSIGNED = "ASSIGNED", _("Assigned")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")
    OVERDUE = "OVERDUE", _("Overdue")


class TaskPriority(models.TextChoices):
    """Priority levels for tasks."""
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


def generate_task_number():
    """Generate a unique task number"""
    return f"TSK-{CodeGenerator.generate_code(length=6, include_alpha=True).upper()}"


class Task(AbstractClusterModel):
    """
    Model representing a task that can be assigned to staff members.
    """
    task_number = models.CharField(
        verbose_name=_("task number"),
        max_length=20,
        unique=True,
        default=generate_task_number,
        help_text=_("Unique task number for tracking"),
    )
    
    title = models.CharField(
        verbose_name=_("task title"),
        max_length=200,
        help_text=_("Brief title describing the task")
    )
    
    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Detailed description of the task")
    )
    
    task_type = models.CharField(
        verbose_name=_("task type"),
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.OTHER,
        help_text=_("Type of task")
    )
    
    priority = models.CharField(
        verbose_name=_("priority"),
        max_length=10,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        help_text=_("Priority level of the task")
    )
    
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        help_text=_("Current status of the task")
    )
    
    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        help_text=_("Staff member assigned to this task")
    )
    
    created_by = models.ForeignKey(
        verbose_name=_("created by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="created_tasks",
        help_text=_("User who created the task")
    )
    
    due_date = models.DateTimeField(
        verbose_name=_("due date"),
        null=True,
        blank=True,
        help_text=_("Expected completion date")
    )
    
    started_at = models.DateTimeField(
        verbose_name=_("started at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when task was started")
    )
    
    completed_at = models.DateTimeField(
        verbose_name=_("completed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when task was completed")
    )
    
    estimated_hours = models.DecimalField(
        verbose_name=_("estimated hours"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Estimated time to complete the task in hours")
    )
    
    actual_hours = models.DecimalField(
        verbose_name=_("actual hours"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Actual time spent on the task in hours")
    )
    
    location = models.CharField(
        verbose_name=_("location"),
        max_length=200,
        blank=True,
        help_text=_("Location where the task should be performed")
    )
    
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the task")
    )
    
    completion_notes = models.TextField(
        verbose_name=_("completion notes"),
        blank=True,
        help_text=_("Notes about task completion")
    )
    
    escalated_at = models.DateTimeField(
        verbose_name=_("escalated at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when task was escalated")
    )
    
    escalated_to = models.ForeignKey(
        verbose_name=_("escalated to"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalated_tasks",
        help_text=_("User the task was escalated to")
    )
    
    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["task_type"]),
            models.Index(fields=["created_at"]),
        ]
    
    def __str__(self):
        return f"{self.task_number} - {self.title}"
    
    def clean(self):
        """Validate task data."""
        super().clean()
        
        if self.due_date and self.due_date <= timezone.now():
            raise ValidationError(_("Due date must be in the future"))
        
        if self.started_at and self.completed_at:
            if self.started_at >= self.completed_at:
                raise ValidationError(_("Start time must be before completion time"))
    
    def save(self, *args, **kwargs):
        """Override save to handle status changes."""
        # Track status changes
        if self.pk:
            old_instance = Task.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == TaskStatus.IN_PROGRESS and not self.started_at:
                    self.started_at = timezone.now()
                elif self.status == TaskStatus.COMPLETED and not self.completed_at:
                    self.completed_at = timezone.now()
                elif self.status == TaskStatus.ASSIGNED and old_instance.status == TaskStatus.PENDING:
                    # Task was just assigned
                    pass
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        return self.due_date and timezone.now() > self.due_date
    
    @property
    def is_due_soon(self):
        """Check if task is due within next 24 hours."""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        if not self.due_date:
            return False
        now = timezone.now()
        return self.due_date > now and self.due_date <= now + timedelta(hours=24)
    
    @property
    def time_remaining(self):
        """Get time remaining until due date."""
        if not self.due_date or self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return None
        return self.due_date - timezone.now()
    
    @property
    def duration_worked(self):
        """Calculate duration worked on the task."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at and self.status == TaskStatus.IN_PROGRESS:
            return timezone.now() - self.started_at
        return timedelta(0)
    
    def assign_to(self, user, assigned_by=None):
        """Assign task to a user."""
        if self.status not in [TaskStatus.PENDING, TaskStatus.ASSIGNED]:
            raise ValidationError(_("Can only assign pending or already assigned tasks"))
        
        old_assignee = self.assigned_to
        self.assigned_to = user
        self.status = TaskStatus.ASSIGNED
        
        if assigned_by:
            self.last_modified_by = assigned_by.id
        
        self.save(update_fields=["last_modified_by"])
        
        # Create assignment history
        TaskAssignmentHistory.objects.create(
            task=self,
            assigned_from=old_assignee,
            assigned_to=user,
            assigned_by=assigned_by,
            cluster=self.cluster
        )
    
    def start_task(self, started_by=None):
        """Start working on the task."""
        if self.status != TaskStatus.ASSIGNED:
            raise ValidationError(_("Can only start assigned tasks"))
        
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = timezone.now()
        
        if started_by:
            self.last_modified_by = started_by.id
        
        self.save()
    
    def complete_task(self, completion_notes="", completed_by=None):
        """Mark task as completed."""
        if self.status != TaskStatus.IN_PROGRESS:
            raise ValidationError(_("Can only complete tasks that are in progress"))
        
        self.status = TaskStatus.COMPLETED
        self.completed_at = timezone.now()
        self.completion_notes = completion_notes
        
        if completed_by:
            self.last_modified_by = completed_by.id
        
        self.save()
    
    def cancel_task(self, reason="", cancelled_by=None):
        """Cancel the task."""
        if self.status == TaskStatus.COMPLETED:
            raise ValidationError(_("Cannot cancel completed tasks"))
        
        self.status = TaskStatus.CANCELLED
        self.notes = f"{self.notes}\n\nCancelled: {reason}".strip()
        
        if cancelled_by:
            self.last_modified_by = cancelled_by.id
        
        self.save()
    
    def escalate_task(self, escalated_to, reason="", escalated_by=None):
        """Escalate the task to another user."""
        self.escalated_to = escalated_to
        self.escalated_at = timezone.now()
        self.notes = f"{self.notes}\n\nEscalated: {reason}".strip()
        
        if escalated_by:
            self.last_modified_by = escalated_by.id
        
        self.save()
        
        # Create escalation history
        TaskEscalationHistory.objects.create(
            task=self,
            escalated_to=escalated_to,
            escalated_by=escalated_by,
            reason=reason,
            cluster=self.cluster
        )


class TaskAssignment(AbstractClusterModel):
    """
    Model for tracking task assignments and reassignments.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    
    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments"
    )
    
    assigned_by = models.ForeignKey(
        verbose_name=_("assigned by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments_made"
    )
    
    assigned_at = models.DateTimeField(
        verbose_name=_("assigned at"),
        auto_now_add=True
    )
    
    notes = models.TextField(
        verbose_name=_("assignment notes"),
        blank=True,
        help_text=_("Notes about the assignment")
    )
    
    class Meta:
        verbose_name = _("task assignment")
        verbose_name_plural = _("task assignments")
        ordering = ["-assigned_at"]
    
    def __str__(self):
        return f"{self.task.task_number} assigned to {self.assigned_to.name}"


class TaskAssignmentHistory(AbstractClusterModel):
    """
    Model for tracking task assignment history.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="assignment_history"
    )
    
    assigned_from = models.ForeignKey(
        verbose_name=_("assigned from"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_assignments_from"
    )
    
    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments_to"
    )
    
    assigned_by = models.ForeignKey(
        verbose_name=_("assigned by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignment_actions"
    )
    
    class Meta:
        verbose_name = _("task assignment history")
        verbose_name_plural = _("task assignment histories")
        ordering = ["-created_at"]
    
    def __str__(self):
        if self.assigned_from:
            return f"{self.task.task_number}: {self.assigned_from.name} → {self.assigned_to.name}"
        return f"{self.task.task_number}: assigned to {self.assigned_to.name}"


class TaskAttachment(AbstractClusterModel):
    """
    Model for file attachments on tasks.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    
    file_name = models.CharField(
        verbose_name=_("file name"),
        max_length=255,
        help_text=_("Original name of the uploaded file")
    )
    
    file_url = models.URLField(
        verbose_name=_("file URL"),
        help_text=_("URL to access the uploaded file")
    )
    
    file_size = models.PositiveIntegerField(
        verbose_name=_("file size"),
        help_text=_("Size of the file in bytes")
    )
    
    file_type = models.CharField(
        verbose_name=_("file type"),
        max_length=100,
        help_text=_("MIME type of the file")
    )
    
    uploaded_by = models.ForeignKey(
        verbose_name=_("uploaded by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_attachments"
    )
    
    attachment_type = models.CharField(
        verbose_name=_("attachment type"),
        max_length=20,
        choices=[
            ('INSTRUCTION', _('Instruction')),
            ('REFERENCE', _('Reference')),
            ('EVIDENCE', _('Evidence')),
            ('COMPLETION', _('Completion')),
            ('OTHER', _('Other')),
        ],
        default='OTHER',
        help_text=_("Type of attachment")
    )
    
    class Meta:
        verbose_name = _("task attachment")
        verbose_name_plural = _("task attachments")
        ordering = ["created_at"]
    
    def __str__(self):
        return f"Attachment for {self.task.task_number}: {self.file_name}"


class TaskStatusHistory(AbstractClusterModel):
    """
    Model to track status changes for tasks.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="status_history"
    )
    
    from_status = models.CharField(
        verbose_name=_("from status"),
        max_length=20,
        choices=TaskStatus.choices,
        null=True,
        blank=True,
        help_text=_("Previous status")
    )
    
    to_status = models.CharField(
        verbose_name=_("to status"),
        max_length=20,
        choices=TaskStatus.choices,
        help_text=_("New status")
    )
    
    changed_by = models.ForeignKey(
        verbose_name=_("changed by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_status_changes"
    )
    
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Notes about the status change")
    )
    
    class Meta:
        verbose_name = _("task status history")
        verbose_name_plural = _("task status histories")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.task.task_number}: {self.from_status} → {self.to_status}"


class TaskEscalationHistory(AbstractClusterModel):
    """
    Model to track task escalations.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="escalation_history"
    )
    
    escalated_to = models.ForeignKey(
        verbose_name=_("escalated to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_escalations_received"
    )
    
    escalated_by = models.ForeignKey(
        verbose_name=_("escalated by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_escalations_made"
    )
    
    reason = models.TextField(
        verbose_name=_("escalation reason"),
        help_text=_("Reason for escalation")
    )
    
    class Meta:
        verbose_name = _("task escalation history")
        verbose_name_plural = _("task escalation histories")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.task.task_number} escalated to {self.escalated_to.name}"


class TaskComment(AbstractClusterModel):
    """
    Model for comments on tasks.
    """
    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="comments"
    )
    
    author = models.ForeignKey(
        verbose_name=_("author"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_comments"
    )
    
    content = models.TextField(
        verbose_name=_("content"),
        help_text=_("Content of the comment")
    )
    
    is_internal = models.BooleanField(
        verbose_name=_("is internal"),
        default=False,
        help_text=_("Whether this comment is internal (staff only)")
    )
    
    parent = models.ForeignKey(
        verbose_name=_("parent comment"),
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )
    
    class Meta:
        verbose_name = _("task comment")
        verbose_name_plural = _("task comments")
        ordering = ["created_at"]
    
    def __str__(self):
        return f"Comment on {self.task.task_number} by {self.author.name}"