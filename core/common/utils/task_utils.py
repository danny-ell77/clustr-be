"""
Task management utilities for ClustR application.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from django.db import models
from django.template import Context

from core.common.models import (
    Task, TaskStatus, TaskPriority, TaskType,
    TaskAssignment, TaskStatusHistory, TaskEscalationHistory
)
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager
from core.common.utils.file_storage import FileStorage

logger = logging.getLogger('clustr')


class TaskManager:
    """
    Utility class for managing tasks and task-related operations.
    """
    
    @staticmethod
    def create_task(
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
        notes: str = ""
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
                status=TaskStatus.ASSIGNED if assigned_to else TaskStatus.PENDING
            )
            
            # Create assignment record if assigned
            if assigned_to:
                TaskAssignment.objects.create(
                    task=task,
                    assigned_to=assigned_to,
                    assigned_by=created_by,
                    cluster=cluster,
                    notes=f"Initial assignment during task creation"
                )
                
                # Send assignment notification
                TaskNotificationManager.send_task_assignment_notification(task, assigned_to)
            
            logger.info(f"Task created: {task.task_number} by {created_by.name}")
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    @staticmethod
    def assign_task(task: Task, assigned_to, assigned_by) -> bool:
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
            TaskNotificationManager.send_task_assignment_notification(task, assigned_to)
            
            logger.info(f"Task {task.task_number} assigned to {assigned_to.name} by {assigned_by.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.task_number}: {e}")
            return False
    
    @staticmethod
    def start_task(task: Task, started_by) -> bool:
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
            TaskNotificationManager.send_task_status_notification(
                task, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, started_by
            )
            
            logger.info(f"Task {task.task_number} started by {started_by.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start task {task.task_number}: {e}")
            return False
    
    @staticmethod
    def complete_task(task: Task, completion_notes: str, completed_by, evidence_files: List = None) -> bool:
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
                    TaskFileManager.upload_task_attachment(
                        task=task,
                        file_obj=file_obj,
                        uploaded_by=completed_by,
                        attachment_type='COMPLETION'
                    )
            
            # Create status history record
            TaskStatusHistory.objects.create(
                task=task,
                from_status=TaskStatus.IN_PROGRESS,
                to_status=TaskStatus.COMPLETED,
                changed_by=completed_by,
                notes=f"Task completed with notes: {completion_notes}",
                cluster=task.cluster
            )
            
            # Send completion notification
            TaskNotificationManager.send_task_completion_notification(task, completed_by)
            
            logger.info(f"Task {task.task_number} completed by {completed_by.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task {task.task_number}: {e}")
            return False
    
    @staticmethod
    def escalate_task(task: Task, escalated_to, reason: str, escalated_by) -> bool:
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
            TaskNotificationManager.send_task_escalation_notification(task, escalated_to, reason)
            
            logger.info(f"Task {task.task_number} escalated to {escalated_to.name} by {escalated_by.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate task {task.task_number}: {e}")
            return False
    
    @staticmethod
    def get_overdue_tasks(cluster) -> List[Task]:
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
            status__in=[TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]
        ).order_by('due_date')
    
    @staticmethod
    def get_due_soon_tasks(cluster, hours: int = 24) -> List[Task]:
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
            status__in=[TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]
        ).order_by('due_date')
    
    @staticmethod
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
        queryset = Task.objects.filter(
            cluster=cluster,
            assigned_to=user
        )
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_task_statistics(cluster) -> dict[str, Any]:
        """
        Get task statistics for a cluster.
        
        Args:
            cluster: Cluster to get statistics for
            
        Returns:
            Dictionary containing task statistics
        """
        tasks = Task.objects.filter(cluster=cluster)
        
        # Status counts
        status_counts = tasks.values('status').annotate(count=Count('id'))
        status_stats = {item['status']: item['count'] for item in status_counts}
        
        # Priority counts
        priority_counts = tasks.values('priority').annotate(count=Count('id'))
        priority_stats = {item['priority']: item['count'] for item in priority_counts}
        
        # Type counts
        type_counts = tasks.values('task_type').annotate(count=Count('id'))
        type_stats = {item['task_type']: item['count'] for item in type_counts}
        
        # Overdue tasks
        overdue_count = len(TaskManager.get_overdue_tasks(cluster))
        
        # Due soon tasks
        due_soon_count = len(TaskManager.get_due_soon_tasks(cluster))
        
        # Average completion time
        completed_tasks = tasks.filter(status=TaskStatus.COMPLETED, started_at__isnull=False, completed_at__isnull=False)
        avg_completion_time = None
        if completed_tasks.exists():
            durations = [(task.completed_at - task.started_at).total_seconds() / 3600 for task in completed_tasks]
            avg_completion_time = sum(durations) / len(durations)
        
        return {
            'total_tasks': tasks.count(),
            'status_breakdown': status_stats,
            'priority_breakdown': priority_stats,
            'type_breakdown': type_stats,
            'overdue_tasks': overdue_count,
            'due_soon_tasks': due_soon_count,
            'average_completion_hours': avg_completion_time,
        }
    
    @staticmethod
    def mark_overdue_tasks(cluster):
        """
        Mark overdue tasks with OVERDUE status.
        
        Args:
            cluster: Cluster to process overdue tasks for
        """
        overdue_tasks = TaskManager.get_overdue_tasks(cluster)
        
        for task in overdue_tasks:
            if task.status != TaskStatus.OVERDUE:
                old_status = task.status
                task.status = TaskStatus.OVERDUE
                task.save()
                
                # Create status history
                TaskStatusHistory.objects.create(
                    task=task,
                    from_status=old_status,
                    to_status=TaskStatus.OVERDUE,
                    changed_by_id=None,  # System change
                    notes="Automatically marked as overdue",
                    cluster=cluster
                )
                
                # Send overdue notification
                TaskNotificationManager.send_task_overdue_notification(task)
                
                logger.info(f"Task {task.task_number} marked as overdue")
    
    @staticmethod
    def send_due_reminders(cluster):
        """
        Send reminders for tasks that are due soon.
        
        Args:
            cluster: Cluster to send reminders for
        """
        due_soon_tasks = TaskManager.get_due_soon_tasks(cluster)
        
        for task in due_soon_tasks:
            if task.assigned_to:
                TaskNotificationManager.send_task_due_reminder(task)
                logger.info(f"Due reminder sent for task {task.task_number}")
    
    @staticmethod
    def process_overdue_tasks(cluster):
        """
        Process overdue tasks by marking them as overdue and escalating if needed.
        
        Args:
            cluster: Cluster to process overdue tasks for
        """
        overdue_tasks = TaskManager.get_overdue_tasks(cluster)
        
        for task in overdue_tasks:
            # Mark as overdue if not already
            if task.status != TaskStatus.OVERDUE:
                TaskManager.mark_overdue_tasks(cluster)
            
            # Check if task needs escalation (overdue for more than 24 hours)
            if task.due_date and timezone.now() > task.due_date + timedelta(hours=24):
                if not task.escalated_at:
                    # Find supervisor to escalate to (this would be configurable in a real system)
                    supervisor = TaskManager._find_supervisor_for_escalation(task)
                    if supervisor:
                        reason = "Task is overdue by more than 24 hours"
                        task.escalate_task(supervisor, reason, None)
                        
                        # Send automatic escalation notification
                        TaskNotificationManager.send_automatic_escalation_notification(
                            task, supervisor, reason
                        )
                        
                        logger.info(f"Task {task.task_number} automatically escalated due to being overdue")
    
    @staticmethod
    def _find_supervisor_for_escalation(task: Task):
        """
        Find an appropriate supervisor to escalate the task to.
        This is a simplified implementation - in a real system this would be more sophisticated.
        
        Args:
            task: Task to find supervisor for
            
        Returns:
            User to escalate to, or None if no supervisor found
        """
        # For now, escalate to the task creator if they're different from the assignee
        if task.created_by != task.assigned_to:
            return task.created_by
        
        # In a real system, you would look up organizational hierarchy
        # For now, return None to indicate no escalation target found
        return None
    
    @staticmethod
    def get_task_performance_analytics(cluster, start_date=None, end_date=None) -> dict[str, Any]:
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
            completed_at__isnull=False
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
        on_time_completed = tasks.filter(
            status=TaskStatus.COMPLETED,
            completed_at__isnull=False,
            due_date__isnull=False
        ).filter(completed_at__lte=models.F('due_date')).count()
        
        late_completed = completed_tasks - on_time_completed
        
        # Escalation statistics
        escalated_tasks = tasks.filter(escalated_at__isnull=False).count()
        escalation_rate = (escalated_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completion_rate': round(completion_rate, 2),
            'overdue_rate': round(overdue_rate, 2),
            'escalation_rate': round(escalation_rate, 2),
            'average_completion_hours': round(avg_completion_hours, 2) if avg_completion_hours else None,
            'priority_breakdown': priority_breakdown,
            'type_breakdown': type_breakdown,
            'on_time_completed': on_time_completed,
            'late_completed': late_completed,
            'escalated_tasks': escalated_tasks,
        }


class TaskNotificationManager:
    """
    Manages task-related notifications.
    """
    
    @staticmethod
    def send_task_assignment_notification(task: Task, assigned_to) -> bool:
        """
        Send notification when a task is assigned.
        
        Args:
            task: The task that was assigned
            assigned_to: User the task was assigned to
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            if not assigned_to:
                return False
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_ASSIGNED, # Using ISSUE_ASSIGNED as a placeholder for now
                recipients=[assigned_to],
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'task_description': task.description[:200] + '...' if len(task.description) > 200 else task.description,
                    'task_type': task.get_task_type_display(),
                    'priority': task.get_priority_display(),
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Not set',
                    'location': task.location or 'Not specified',
                    'created_by_name': task.created_by.name,
                    'assigned_to_name': assigned_to.name,
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task assignment notification: {e}")
            return False
    
    @staticmethod
    def send_task_status_notification(task: Task, old_status: str, new_status: str, changed_by) -> bool:
        """
        Send notification when task status changes.
        
        Args:
            task: The task whose status changed
            old_status: Previous status
            new_status: New status
            changed_by: User who changed the status
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
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
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_STATUS_CHANGED, # Using ISSUE_STATUS_CHANGED as a placeholder for now
                recipients=recipients,
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by_name': changed_by.name,
                    'task_type': task.get_task_type_display(),
                    'priority': task.get_priority_display(),
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task status notification: {e}")
            return False
    
    @staticmethod
    def send_task_completion_notification(task: Task, completed_by) -> bool:
        """
        Send notification when a task is completed.
        
        Args:
            task: The completed task
            completed_by: User who completed the task
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
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
            
            # Check if completion evidence was provided
            from core.common.utils.task_utils import TaskFileManager
            evidence_files = TaskFileManager.get_completion_evidence(task)
            has_evidence = len(evidence_files) > 0
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_STATUS_CHANGED,
                recipients=recipients,
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'completed_by_name': completed_by.name,
                    'completion_date': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else 'Unknown',
                    'completion_notes': task.completion_notes or 'No additional notes',
                    'task_type': task.get_task_type_display(),
                    'duration_worked': str(task.duration_worked) if task.duration_worked else 'Unknown',
                    'has_evidence': has_evidence,
                    'evidence_count': len(evidence_files),
                    'was_on_time': task.due_date and task.completed_at and task.completed_at <= task.due_date,
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task completion notification: {e}")
            return False
    
    @staticmethod
    def send_task_escalation_notification(task: Task, escalated_to, reason: str) -> bool:
        """
        Send notification when a task is escalated.
        
        Args:
            task: The escalated task
            escalated_to: User the task was escalated to
            reason: Reason for escalation
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            if not escalated_to:
                return False
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_ESCALATED,
                recipients=[escalated_to],
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'task_description': task.description[:200] + '...' if len(task.description) > 200 else task.description,
                    'escalation_reason': reason,
                    'task_type': task.get_task_type_display(),
                    'priority': task.get_priority_display(),
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Not set',
                    'assigned_to_name': task.assigned_to.name if task.assigned_to else 'Unassigned',
                    'escalated_to_name': escalated_to.name,
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task escalation notification: {e}")
            return False
    
    @staticmethod
    def send_task_due_reminder(task: Task) -> bool:
        """
        Send reminder when a task is due soon.
        
        Args:
            task: The task that is due soon
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            if not task.assigned_to:
                return False
            
            NotificationManager.send(
                event=NotificationEvents.TASK_DUE,
                recipients=[task.assigned_to],
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Not set',
                    'time_remaining': str(task.time_remaining) if task.time_remaining else 'Overdue',
                    'priority': task.get_priority_display(),
                    'task_type': task.get_task_type_display(),
                    'assigned_to_name': task.assigned_to.name,
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task due reminder: {e}")
            return False
    
    @staticmethod
    def send_task_overdue_notification(task: Task) -> bool:
        """
        Send notification when a task becomes overdue.
        
        Args:
            task: The overdue task
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            recipients = []
            
            # Notify assigned user
            if task.assigned_to:
                recipients.append(task.assigned_to)
            
            # Notify task creator
            if task.created_by and task.created_by != task.assigned_to:
                recipients.append(task.created_by)
            
            if not recipients:
                return True
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_OVERDUE,
                recipients=recipients,
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Not set',
                    'days_overdue': (timezone.now() - task.due_date).days if task.due_date else 0,
                    'priority': task.get_priority_display(),
                    'task_type': task.get_task_type_display(),
                    'assigned_to_name': task.assigned_to.name if task.assigned_to else 'Unassigned',
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task overdue notification: {e}")
            return False
    
    @staticmethod
    def send_automatic_escalation_notification(task: Task, escalated_to, reason: str) -> bool:
        """
        Send notification when a task is automatically escalated due to being overdue.
        
        Args:
            task: The escalated task
            escalated_to: User the task was escalated to
            reason: Reason for escalation
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            recipients = []
            
            # Notify the person the task was escalated to
            if escalated_to:
                recipients.append(escalated_to)
            
            # Notify the original assignee
            if task.assigned_to and task.assigned_to != escalated_to:
                recipients.append(task.assigned_to)
            
            if not recipients:
                return True
            
            days_overdue = (timezone.now() - task.due_date).days if task.due_date else 0
            
            NotificationManager.send(
                event=NotificationEvents.ISSUE_AUTO_ESCALATED,
                recipients=recipients,
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'task_description': task.description[:200] + '...' if len(task.description) > 200 else task.description,
                    'escalation_reason': reason,
                    'task_type': task.get_task_type_display(),
                    'priority': task.get_priority_display(),
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Not set',
                    'days_overdue': days_overdue,
                    'assigned_to_name': task.assigned_to.name if task.assigned_to else 'Unassigned',
                    'escalated_to_name': escalated_to.name,
                    'is_automatic': True,
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send automatic escalation notification: {e}")
            return False

    @staticmethod
    def send_task_comment_notification(comment, task: Task) -> bool:
        """
        Send notification when a comment is added to a task.
        
        Args:
            comment: The comment object that was added
            task: The task the comment was added to
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
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
            
            NotificationManager.send(
                event=NotificationEvents.COMMENT_REPLY,
                recipients=recipients,
                cluster=task.cluster,
                context={
                    'task_number': task.task_number,
                    'task_title': task.title,
                    'comment_text': comment.comment[:200] + '...' if len(comment.comment) > 200 else comment.comment,
                    'commenter_name': comment.created_by.name,
                    'comment_date': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                    'task_type': task.get_task_type_display(),
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task comment notification: {e}")
            return False


class TaskFileManager:
    """
    Manages file attachments for tasks.
    """
    
    @staticmethod
    def upload_task_attachment(task: Task, file_obj, uploaded_by, attachment_type: str = 'OTHER') -> str:
        """
        Upload a file attachment for a task.
        
        Args:
            task: Task to attach file to
            file_obj: File object to upload
            uploaded_by: User uploading the file
            attachment_type: Type of attachment
            
        Returns:
            URL of the uploaded file
        """
        try:
            # Upload file using FileStorage utility
            file_url = FileStorage.upload_file(
                file_obj,
                folder=f'tasks/{task.task_number}',
                cluster_id=str(task.cluster.id)
            )
            
            # Create attachment record
            from core.common.models import TaskAttachment
            attachment = TaskAttachment.objects.create(
                task=task,
                file_name=file_obj.name,
                file_url=file_url,
                file_size=file_obj.size,
                file_type=file_obj.content_type,
                uploaded_by=uploaded_by,
                attachment_type=attachment_type,
                cluster=task.cluster
            )
            
            logger.info(f"File attachment uploaded for task {task.task_number}: {file_obj.name}")
            return file_url
            
        except Exception as e:
            logger.error(f"Failed to upload task attachment: {e}")
            raise
    
    @staticmethod
    def upload_completion_evidence(task: Task, evidence_files: List, completed_by) -> List[str]:
        """
        Upload multiple evidence files for task completion.
        
        Args:
            task: Task to attach evidence to
            evidence_files: List of file objects
            completed_by: User completing the task
            
        Returns:
            List of URLs of uploaded files
        """
        uploaded_urls = []
        
        try:
            for file_obj in evidence_files:
                file_url = TaskFileManager.upload_task_attachment(
                    task=task,
                    file_obj=file_obj,
                    uploaded_by=completed_by,
                    attachment_type='EVIDENCE'
                )
                uploaded_urls.append(file_url)
            
            logger.info(f"Uploaded {len(uploaded_urls)} evidence files for task {task.task_number}")
            return uploaded_urls
            
        except Exception as e:
            logger.error(f"Failed to upload completion evidence: {e}")
            # Clean up any successfully uploaded files
            for url in uploaded_urls:
                try:
                    # Extract file path from URL and delete
                    # This is a simplified approach - in a real system you'd need proper cleanup
                    pass
                except:
                    pass
            raise
    
    @staticmethod
    def get_task_attachments(task: Task, attachment_type: str = None) -> List:
        """
        Get attachments for a task, optionally filtered by type.
        
        Args:
            task: Task to get attachments for
            attachment_type: Optional attachment type filter
            
        Returns:
            List of task attachments
        """
        from core.common.models import TaskAttachment
        
        queryset = TaskAttachment.objects.filter(task=task)
        
        if attachment_type:
            queryset = queryset.filter(attachment_type=attachment_type)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_completion_evidence(task: Task) -> List:
        """
        Get completion evidence attachments for a task.
        
        Args:
            task: Task to get evidence for
            
        Returns:
            List of evidence attachments
        """
        return TaskFileManager.get_task_attachments(task, 'EVIDENCE')
    
    @staticmethod
    def validate_evidence_files(files: List) -> dict[str, Any]:
        """
        Validate evidence files before upload.
        
        Args:
            files: List of file objects to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not files:
            validation_result['valid'] = False
            validation_result['errors'].append("At least one evidence file is required for task completion")
            return validation_result
        
        for i, file_obj in enumerate(files):
            # Check file size
            if not FileStorage.validate_file_size(file_obj.size, file_obj.name):
                validation_result['valid'] = False
                validation_result['errors'].append(f"File {i+1} ({file_obj.name}) exceeds maximum size limit")
            
            # Check file type
            file_category = FileStorage.get_file_type_category(file_obj.name)
            if file_category == 'other':
                validation_result['warnings'].append(f"File {i+1} ({file_obj.name}) has an unknown file type")
        
        return validation_result