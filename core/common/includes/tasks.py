"""
Tasks utilities for ClustR application.
Refactored from TaskManager static methods to pure functions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Any
from django.utils import timezone
from django.db.models import Count
from django.db import models

from core.common.models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskAssignment,
    TaskStatusHistory,
)
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

logger = logging.getLogger("clustr")


def create(
    title: str,
    description: str,
    created_by,
    cluster,
    task_type: str = TaskType.OTHER,
    priority: str = TaskPriority.MEDIUM,
    assigned_to=None,
    due_date: datetime = None,
    location: str = "",
    estimated_hours: float = None,
    notes: str = "",
) -> Task:
    """
    Create a new task.

    Args:
        title: Task title
        description: Task description
        created_by: User creating the task
        cluster: Cluster the task belongs to
        task_type: Type of task
        priority: Priority level
        assigned_to: User to assign the task to (optional)
        due_date: Due date for the task (optional)
        location: Location where task should be performed
        estimated_hours: Estimated hours to complete
        notes: Additional notes

    Returns:
        The created Task instance
    """
    try:
        task = Task.objects.create(
            title=title,
            description=description,
            created_by=created_by,
            cluster=cluster,
            task_type=task_type,
            priority=priority,
            assigned_to=assigned_to,
            due_date=due_date,
            location=location,
            estimated_hours=estimated_hours,
            notes=notes,
            status=TaskStatus.ASSIGNED if assigned_to else TaskStatus.PENDING,
        )

        # Create assignment record if assigned
        if assigned_to:
            TaskAssignment.objects.create(
                task=task,
                assigned_to=assigned_to,
                assigned_by=created_by,
                cluster=cluster,
                notes="Initial assignment during task creation",
            )

            # Send assignment notification
            send_assignment_notification(task, assigned_to)

        logger.info(f"Task created: {task.task_number} by {created_by.name}")
        return task

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise


def assign(task: Task, assigned_to, assigned_by) -> bool:
    """
    Assign a task to a user.

    Args:
        task: Task to assign
        assigned_to: User to assign the task to
        assigned_by: User making the assignment

    Returns:
        True if assignment was successful, False otherwise
    """
    try:
        task.assign_to(assigned_to, assigned_by)

        # Send assignment notification
        send_assignment_notification(task, assigned_to)

        logger.info(
            f"Task {task.task_number} assigned to {assigned_to.name} by {assigned_by.name}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to assign task {task.task_number}: {e}")
        return False


def start(task: Task, started_by) -> bool:
    """
    Start working on a task.

    Args:
        task: Task to start
        started_by: User starting the task

    Returns:
        True if task was started successfully, False otherwise
    """
    try:
        task.start_task(started_by)

        # Send status change notification
        send_status_notification(
            task, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, started_by
        )

        logger.info(f"Task {task.task_number} started by {started_by.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to start task {task.task_number}: {e}")
        return False


def complete(
    task: Task, completion_notes: str, completed_by, evidence_files: List = None
) -> bool:
    """
    Complete a task with optional evidence attachments.

    Args:
        task: Task to complete
        completion_notes: Notes about task completion
        completed_by: User completing the task
        evidence_files: Optional list of evidence files to attach

    Returns:
        True if task was completed successfully, False otherwise
    """
    try:
        # Complete the task
        task.complete_task(completion_notes, completed_by)

        # Attach evidence files if provided
        if evidence_files:
            for file_obj in evidence_files:
                upload_attachment(
                    task=task,
                    file_obj=file_obj,
                    uploaded_by=completed_by,
                    attachment_type="COMPLETION",
                )

        # Create status history record
        TaskStatusHistory.objects.create(
            task=task,
            from_status=TaskStatus.IN_PROGRESS,
            to_status=TaskStatus.COMPLETED,
            changed_by=completed_by,
            notes=f"Task completed with notes: {completion_notes}",
            cluster=task.cluster,
        )

        # Send completion notification
        send_completion_notification(task, completed_by)

        logger.info(f"Task {task.task_number} completed by {completed_by.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to complete task {task.task_number}: {e}")
        return False


def escalate(task: Task, escalated_to, reason: str, escalated_by) -> bool:
    """
    Escalate a task to another user.

    Args:
        task: Task to escalate
        escalated_to: User to escalate the task to
        reason: Reason for escalation
        escalated_by: User making the escalation

    Returns:
        True if escalation was successful, False otherwise
    """
    try:
        task.escalate_task(escalated_to, reason, escalated_by)

        # Send escalation notification
        send_escalation_notification(task, escalated_to, reason)

        logger.info(
            f"Task {task.task_number} escalated to {escalated_to.name} by {escalated_by.name}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to escalate task {task.task_number}: {e}")
        return False


def get_overdue(cluster) -> List[Task]:
    """
    Get all overdue tasks for a cluster.

    Args:
        cluster: Cluster to get overdue tasks for

    Returns:
        List of overdue tasks
    """
    now = timezone.now()
    return Task.objects.filter(
        cluster=cluster,
        due_date__lt=now,
        status__in=[TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS],
    ).order_by("due_date")


def get_due_soon(cluster, hours: int = 24) -> List[Task]:
    """
    Get tasks that are due soon.

    Args:
        cluster: Cluster to get tasks for
        hours: Number of hours to look ahead (default 24)

    Returns:
        List of tasks due soon
    """
    now = timezone.now()
    due_threshold = now + timedelta(hours=hours)

    return Task.objects.filter(
        cluster=cluster,
        due_date__gte=now,
        due_date__lte=due_threshold,
        status__in=[TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS],
    ).order_by("due_date")


def get_user_tasks(user, cluster, status: str = None) -> List[Task]:
    """
    Get tasks assigned to a specific user.

    Args:
        user: User to get tasks for
        cluster: Cluster to filter by
        status: Optional status filter

    Returns:
        List of user's tasks
    """
    queryset = Task.objects.filter(cluster=cluster, assigned_to=user)

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


def get_statistics(cluster) -> dict[str, Any]:
    """
    Get task statistics for a cluster.

    Args:
        cluster: Cluster to get statistics for

    Returns:
        Dictionary containing task statistics
    """
    tasks = Task.objects.filter(cluster=cluster)

    # Status counts
    status_counts = tasks.values("status").annotate(count=Count("id"))
    status_stats = {item["status"]: item["count"] for item in status_counts}

    # Priority counts
    priority_counts = tasks.values("priority").annotate(count=Count("id"))
    priority_stats = {item["priority"]: item["count"] for item in priority_counts}

    # Type counts
    type_counts = tasks.values("task_type").annotate(count=Count("id"))
    type_stats = {item["task_type"]: item["count"] for item in type_counts}

    # Overdue tasks
    overdue_count = len(get_overdue(cluster))

    # Due soon tasks
    due_soon_count = len(get_due_soon(cluster))

    # Average completion time
    completed_tasks = tasks.filter(
        status=TaskStatus.COMPLETED,
        started_at__isnull=False,
        completed_at__isnull=False,
    )
    avg_completion_time = None
    if completed_tasks.exists():
        durations = [
            (task.completed_at - task.started_at).total_seconds() / 3600
            for task in completed_tasks
        ]
        avg_completion_time = sum(durations) / len(durations)

    return {
        "total_tasks": tasks.count(),
        "status_breakdown": status_stats,
        "priority_breakdown": priority_stats,
        "type_breakdown": type_stats,
        "overdue_tasks": overdue_count,
        "due_soon_tasks": due_soon_count,
        "average_completion_hours": avg_completion_time,
    }


def get_performance_analytics(
    cluster, start_date=None, end_date=None
) -> dict[str, Any]:
    """
    Get task performance analytics for a cluster.

    Args:
        cluster: Cluster to get analytics for
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering

    Returns:
        Dictionary containing performance analytics
    """
    tasks = Task.objects.filter(cluster=cluster)

    # Apply date filters if provided
    if start_date:
        tasks = tasks.filter(created_at__gte=start_date)
    if end_date:
        tasks = tasks.filter(created_at__lte=end_date)

    # Basic statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=TaskStatus.COMPLETED).count()
    overdue_tasks = tasks.filter(status=TaskStatus.OVERDUE).count()
    in_progress_tasks = tasks.filter(status=TaskStatus.IN_PROGRESS).count()

    # Completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Average completion time for completed tasks
    completed_with_times = tasks.filter(
        status=TaskStatus.COMPLETED,
        started_at__isnull=False,
        completed_at__isnull=False,
    )

    avg_completion_hours = None
    if completed_with_times.exists():
        durations = [
            (task.completed_at - task.started_at).total_seconds() / 3600
            for task in completed_with_times
        ]
        avg_completion_hours = sum(durations) / len(durations)

    # Tasks by priority
    priority_breakdown = {}
    for priority in TaskPriority.choices:
        priority_breakdown[priority[0]] = tasks.filter(priority=priority[0]).count()

    # Tasks by type
    type_breakdown = {}
    for task_type in TaskType.choices:
        type_breakdown[task_type[0]] = tasks.filter(task_type=task_type[0]).count()

    # Overdue rate
    overdue_rate = (overdue_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Tasks completed on time vs overdue
    on_time_completed = (
        tasks.filter(
            status=TaskStatus.COMPLETED,
            completed_at__isnull=False,
            due_date__isnull=False,
        )
        .filter(completed_at__lte=models.F("due_date"))
        .count()
    )

    late_completed = completed_tasks - on_time_completed

    # Escalation statistics
    escalated_tasks = tasks.filter(escalated_at__isnull=False).count()
    escalation_rate = (escalated_tasks / total_tasks * 100) if total_tasks > 0 else 0

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completion_rate": round(completion_rate, 2),
        "overdue_rate": round(overdue_rate, 2),
        "escalation_rate": round(escalation_rate, 2),
        "average_completion_hours": (
            round(avg_completion_hours, 2) if avg_completion_hours else None
        ),
        "priority_breakdown": priority_breakdown,
        "type_breakdown": type_breakdown,
        "on_time_completed": on_time_completed,
        "late_completed": late_completed,
        "escalated_tasks": escalated_tasks,
    }


# Task notification helper functions
def send_assignment_notification(task: Task, assigned_to) -> bool:
    """Send notification when a task is assigned."""
    try:
        if not assigned_to:
            return False

        notifications.send(
            event_name=NotificationEvents.ISSUE_ASSIGNED,  # Using ISSUE_ASSIGNED as a placeholder for now
            recipients=[assigned_to],
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "task_description": (
                    task.description[:200] + "..."
                    if len(task.description) > 200
                    else task.description
                ),
                "task_type": task.get_task_type_display(),
                "priority": task.get_priority_display(),
                "due_date": (
                    task.due_date.strftime("%Y-%m-%d %H:%M")
                    if task.due_date
                    else "Not set"
                ),
                "location": task.location or "Not specified",
                "created_by_name": task.created_by.name,
                "assigned_to_name": assigned_to.name,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task assignment notification: {e}")
        return False


def send_status_notification(
    task: Task, old_status: str, new_status: str, changed_by
) -> bool:
    """Send notification when task status changes."""
    try:
        recipients = []

        # Notify task creator if they're not the one making the change
        if task.created_by != changed_by:
            recipients.append(task.created_by)

        # Notify assigned user if they're not the one making the change
        if task.assigned_to and task.assigned_to != changed_by:
            recipients.append(task.assigned_to)

        if not recipients:
            return True

        notifications.send(
            event_name=NotificationEvents.ISSUE_STATUS_CHANGED,  # Using ISSUE_STATUS_CHANGED as a placeholder for now
            recipients=recipients,
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by_name": changed_by.name,
                "task_type": task.get_task_type_display(),
                "priority": task.get_priority_display(),
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task status notification: {e}")
        return False


def send_completion_notification(task: Task, completed_by) -> bool:
    """Send notification when a task is completed."""
    try:
        recipients = []

        # Notify task creator if they're not the one completing the task
        if task.created_by != completed_by:
            recipients.append(task.created_by)

        # If task was escalated, notify the escalated person
        if task.escalated_to and task.escalated_to != completed_by:
            recipients.append(task.escalated_to)

        if not recipients:
            return True

        notifications.send(
            event_name=NotificationEvents.ISSUE_STATUS_CHANGED,
            recipients=recipients,
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "completed_by_name": completed_by.name,
                "completion_date": (
                    task.completed_at.strftime("%Y-%m-%d %H:%M")
                    if task.completed_at
                    else "Unknown"
                ),
                "completion_notes": task.completion_notes or "No additional notes",
                "task_type": task.get_task_type_display(),
                "duration_worked": (
                    str(task.duration_worked) if task.duration_worked else "Unknown"
                ),
                "was_on_time": task.due_date
                and task.completed_at
                and task.completed_at <= task.due_date,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task completion notification: {e}")
        return False


def send_escalation_notification(task: Task, escalated_to, reason: str) -> bool:
    """Send notification when a task is escalated."""
    try:
        if not escalated_to:
            return False

        notifications.send(
            event_name=NotificationEvents.ISSUE_ESCALATED,
            recipients=[escalated_to],
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "task_description": (
                    task.description[:200] + "..."
                    if len(task.description) > 200
                    else task.description
                ),
                "escalation_reason": reason,
                "task_type": task.get_task_type_display(),
                "priority": task.get_priority_display(),
                "due_date": (
                    task.due_date.strftime("%Y-%m-%d %H:%M")
                    if task.due_date
                    else "Not set"
                ),
                "assigned_to_name": (
                    task.assigned_to.name if task.assigned_to else "Unassigned"
                ),
                "escalated_to_name": escalated_to.name,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task escalation notification: {e}")
        return False


# Task file management functions
def upload_attachment(task, file_obj, uploaded_by, attachment_type="general"):
    """Upload an attachment for a task."""
    try:
        from core.common.includes.file_storage import FileStorage
        from core.common.models import TaskAttachment

        # Use FileStorage to handle the upload
        file_url = FileStorage.upload_file(
            file_obj,
            folder=f"tasks/{task.id}",
            allowed_extensions=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
        )

        attachment = TaskAttachment.objects.create(
            task=task,
            file_url=file_url,
            file_name=file_obj.name,
            file_size=file_obj.size,
            attachment_type=attachment_type,
            uploaded_by=uploaded_by,
        )

        logger.info(f"Task attachment uploaded: {attachment.id}")
        return file_url

    except Exception as e:
        logger.error(f"Failed to upload task attachment: {e}")
        raise


def validate_evidence_files(evidence_files):
    """Validate evidence files for task completion."""
    try:
        if not evidence_files:
            return {"valid": True, "message": "No files to validate"}

        allowed_extensions = ["jpg", "jpeg", "png", "pdf", "doc", "docx"]
        max_file_size = 10 * 1024 * 1024  # 10MB

        for file_obj in evidence_files:
            # Check file extension
            file_extension = file_obj.name.split(".")[-1].lower()
            if file_extension not in allowed_extensions:
                return {
                    "valid": False,
                    "message": f'File type .{file_extension} not allowed. Allowed types: {", ".join(allowed_extensions)}',
                }

            # Check file size
            if file_obj.size > max_file_size:
                return {
                    "valid": False,
                    "message": f"File {file_obj.name} is too large. Maximum size is 10MB.",
                }

        return {"valid": True, "message": "All files are valid"}

    except Exception as e:
        logger.error(f"Error validating evidence files: {e}")
        return {"valid": False, "message": "Error validating files"}


def get_completion_evidence(task):
    """Get completion evidence files for a task."""
    try:
        from core.common.models import TaskAttachment

        evidence_attachments = TaskAttachment.objects.filter(
            task=task, attachment_type="COMPLETION"
        ).order_by("-created_at")

        return [
            {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "file_size": attachment.file_size,
                "uploaded_at": attachment.created_at,
                "uploaded_by": (
                    attachment.uploaded_by.name if attachment.uploaded_by else "Unknown"
                ),
            }
            for attachment in evidence_attachments
        ]

    except Exception as e:
        logger.error(f"Error getting completion evidence: {e}")
        return []


def send_comment_notification(comment, task) -> bool:
    """Send notification when a comment is added to a task."""
    try:
        recipients = []

        # Notify task creator if they're not the one commenting
        if task.created_by != comment.created_by:
            recipients.append(task.created_by)

        # Notify assigned user if they're not the one commenting
        if task.assigned_to and task.assigned_to != comment.created_by:
            recipients.append(task.assigned_to)

        # Remove duplicates
        recipients = list(set(recipients))

        if not recipients:
            return True

        notifications.send(
            event_name=NotificationEvents.COMMENT_ADDED,
            recipients=recipients,
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "comment_text": (
                    comment.comment[:200] + "..."
                    if len(comment.comment) > 200
                    else comment.comment
                ),
                "commenter_name": comment.created_by.name,
                "comment_date": comment.created_at.strftime("%Y-%m-%d %H:%M"),
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task comment notification: {e}")
        return False


def send_task_due_reminder(task: Task) -> bool:
    """
    Send reminder when a task is due soon.
    """
    try:
        if not task.assigned_to:
            return False

        notifications.send(
            event_name=NotificationEvents.TASK_DUE,
            recipients=[task.assigned_to],
            cluster=task.cluster,
            context={
                "task_number": task.task_number,
                "task_title": task.title,
                "due_date": (
                    task.due_date.strftime("%Y-%m-%d %H:%M")
                    if task.due_date
                    else "Not set"
                ),
                "time_remaining": (
                    str(task.time_remaining) if task.time_remaining else "Overdue"
                ),
                "priority": task.get_priority_display(),
                "task_type": task.get_task_type_display(),
                "assigned_to_name": task.assigned_to.name,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send task due reminder: {e}")
        return False
def check_deadlines():
    """Check task deadlines across all clusters and send notifications."""
    from core.common.models import Cluster
    
    for cluster in Cluster.objects.all():
        try:
            # Get overdue tasks
            overdue_tasks = get_overdue(cluster)
            for task in overdue_tasks:
                escalate(
                    task, 
                    task.created_by, 
                    "Task is overdue", 
                    task.created_by
                )
            
            # Get tasks due soon
            due_soon_tasks = get_due_soon(cluster)
            for task in due_soon_tasks:
                send_task_due_reminder(task)
                
            logger.info(f"Completed task deadline checks for cluster: {cluster.name}")
            
        except Exception as e:
            logger.error(f"Error checking task deadlines for cluster {cluster.id}: {e}")
    
    logger.info("Completed task deadline checks for all clusters")