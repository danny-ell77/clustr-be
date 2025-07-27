"""
Utility functions for helpdesk system.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from core.common.models.helpdesk import IssueTicket, IssueStatus
from core.common.utils.notification_utils import NotificationManager

logger = logging.getLogger('clustr')


class HelpdeskManager:
    """
    Manager for helpdesk-related operations and scheduled tasks.
    """
    
    @staticmethod
    def escalate_overdue_issues(days_threshold=3):
        """
        Escalate issues that have been open for more than the specified threshold.
        
        Args:
            days_threshold: Number of days after which to escalate issues
        
        Returns:
            Number of issues escalated
        """
        try:
            threshold_date = timezone.now() - timedelta(days=days_threshold)
            
            # Find issues that are overdue for escalation
            overdue_issues = IssueTicket.objects.filter(
                created_at__lte=threshold_date,
                status__in=[
                    IssueStatus.SUBMITTED,
                    IssueStatus.OPEN,
                    IssueStatus.IN_PROGRESS,
                    IssueStatus.PENDING
                ],
                escalated_at__isnull=True,  # Not already escalated
                priority__in=['LOW', 'MEDIUM']  # Don't escalate already high priority issues
            )
            
            escalated_count = 0
            for issue in overdue_issues:
                issue.escalated_at = timezone.now()
                issue.priority = 'HIGH'
                issue.save()
                
                # Send escalation notification
                NotificationManager.send_issue_escalation_notification(issue)
                escalated_count += 1
                
                logger.info(f"Escalated issue {issue.issue_no} due to being overdue")
            
            return escalated_count
            
        except Exception as e:
            logger.error(f"Error escalating overdue issues: {e}")
            return 0
    
    @staticmethod
    def send_due_date_reminders():
        """
        Send reminders for issues approaching their due date.
        
        Returns:
            Number of reminders sent
        """
        try:
            tomorrow = timezone.now() + timedelta(days=1)
            
            # Find issues due tomorrow that are still open
            due_issues = IssueTicket.objects.filter(
                due_date__date=tomorrow.date(),
                status__in=[
                    IssueStatus.SUBMITTED,
                    IssueStatus.OPEN,
                    IssueStatus.IN_PROGRESS,
                    IssueStatus.PENDING
                ],
                assigned_to__isnull=False
            ).select_related('assigned_to', 'reported_by')
            
            reminders_sent = 0
            for issue in due_issues:
                # Send reminder to assigned staff
                if issue.assigned_to and issue.assigned_to.email_address:
                    success = NotificationManager.send_issue_due_reminder(issue)
                    if success:
                        reminders_sent += 1
                        logger.info(f"Sent due date reminder for issue {issue.issue_no}")
            
            return reminders_sent
            
        except Exception as e:
            logger.error(f"Error sending due date reminders: {e}")
            return 0
    
    @staticmethod
    def auto_close_resolved_issues(days_threshold=7):
        """
        Automatically close issues that have been resolved for a specified period.
        
        Args:
            days_threshold: Number of days after resolution to auto-close
        
        Returns:
            Number of issues closed
        """
        try:
            threshold_date = timezone.now() - timedelta(days=days_threshold)
            
            # Find resolved issues that should be auto-closed
            resolved_issues = IssueTicket.objects.filter(
                status=IssueStatus.RESOLVED,
                resolved_at__lte=threshold_date,
                closed_at__isnull=True
            )
            
            closed_count = 0
            for issue in resolved_issues:
                issue.status = IssueStatus.CLOSED
                issue.closed_at = timezone.now()
                issue.save()
                
                # Notify the reporter that their issue was auto-closed
                if issue.reported_by and issue.reported_by.email_address:
                    NotificationManager.send_issue_auto_close_notification(issue)
                
                closed_count += 1
                logger.info(f"Auto-closed issue {issue.issue_no} after {days_threshold} days")
            
            return closed_count
            
        except Exception as e:
            logger.error(f"Error auto-closing resolved issues: {e}")
            return 0
    
    @staticmethod
    def get_issue_metrics(cluster=None):
        """
        Get comprehensive metrics for issues.
        
        Args:
            cluster: Optional cluster to filter by
        
        Returns:
            Dictionary containing various issue metrics
        """
        try:
            queryset = IssueTicket.objects.all()
            if cluster:
                queryset = queryset.filter(cluster=cluster)
            
            now = timezone.now()
            
            metrics = {
                'total_issues': queryset.count(),
                'open_issues': queryset.filter(status__in=[
                    IssueStatus.SUBMITTED,
                    IssueStatus.OPEN,
                    IssueStatus.IN_PROGRESS,
                    IssueStatus.PENDING
                ]).count(),
                'resolved_issues': queryset.filter(status=IssueStatus.RESOLVED).count(),
                'closed_issues': queryset.filter(status=IssueStatus.CLOSED).count(),
                'escalated_issues': queryset.filter(escalated_at__isnull=False).count(),
                'overdue_issues': queryset.filter(
                    due_date__lt=now,
                    status__in=[
                        IssueStatus.SUBMITTED,
                        IssueStatus.OPEN,
                        IssueStatus.IN_PROGRESS,
                        IssueStatus.PENDING
                    ]
                ).count(),
                'unassigned_issues': queryset.filter(
                    assigned_to__isnull=True,
                    status__in=[
                        IssueStatus.SUBMITTED,
                        IssueStatus.OPEN
                    ]
                ).count(),
            }
            
            # Calculate average resolution time
            resolved_issues = queryset.filter(
                status__in=[IssueStatus.RESOLVED, IssueStatus.CLOSED],
                resolved_at__isnull=False
            )
            
            if resolved_issues.exists():
                total_resolution_time = sum([
                    (issue.resolved_at - issue.created_at).total_seconds()
                    for issue in resolved_issues
                ])
                avg_resolution_hours = total_resolution_time / resolved_issues.count() / 3600
                metrics['avg_resolution_hours'] = round(avg_resolution_hours, 2)
            else:
                metrics['avg_resolution_hours'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating issue metrics: {e}")
            return {}
    
    @staticmethod
    def search_issues(query, cluster=None, user=None):
        """
        Search issues by various criteria.
        
        Args:
            query: Search query string
            cluster: Optional cluster to filter by
            user: Optional user to filter by (for user's own issues)
        
        Returns:
            QuerySet of matching issues
        """
        try:
            queryset = IssueTicket.objects.all()
            
            if cluster:
                queryset = queryset.filter(cluster=cluster)
            
            if user:
                queryset = queryset.filter(reported_by=user)
            
            if query:
                queryset = queryset.filter(
                    Q(issue_no__icontains=query) |
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(reported_by__name__icontains=query) |
                    Q(assigned_to__name__icontains=query) |
                    Q(resolution_notes__icontains=query)
                )
            
            return queryset.select_related(
                'reported_by',
                'assigned_to',
                'cluster'
            ).prefetch_related(
                'comments',
                'attachments',
                'status_history'
            )
            
        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            return IssueTicket.objects.none()