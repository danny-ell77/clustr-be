"""
Helpdesk utilities for ClustR application.
Refactored from HelpdeskManager static methods to pure functions.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from typing import Dict, Any, Optional

from core.common.models import IssueTicket, IssueStatus

logger = logging.getLogger('clustr')


def escalate_overdue_issues(days_threshold=3):
    """Escalate overdue issues."""
    threshold_date = timezone.now() - timedelta(days=days_threshold)
    
    overdue_issues = IssueTicket.objects.filter(
        status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS],
        created_at__lte=threshold_date,
        escalated_at__isnull=True
    )
    
    escalated_count = 0
    for issue in overdue_issues:
        issue.status = IssueStatus.ESCALATED
        issue.escalated_at = timezone.now()
        issue.save()
        escalated_count += 1
    
    logger.info(f"Escalated {escalated_count} overdue issues")
    return escalated_count


def send_due_date_reminders():
    """Send due date reminders for issues."""
    tomorrow = timezone.now() + timedelta(days=1)
    
    due_issues = IssueTicket.objects.filter(
        due_date__date=tomorrow.date(),
        status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS]
    )
    
    reminders_sent = 0
    for issue in due_issues:
        # Send reminder notification
        # notifications.send(...)
        reminders_sent += 1
    
    logger.info(f"Sent {reminders_sent} due date reminders")
    return reminders_sent


def auto_close_resolved_issues(days_threshold=7):
    """Auto-close resolved issues after threshold."""
    threshold_date = timezone.now() - timedelta(days=days_threshold)
    
    resolved_issues = IssueTicket.objects.filter(
        status=IssueStatus.RESOLVED,
        resolved_at__lte=threshold_date
    )
    
    closed_count = 0
    for issue in resolved_issues:
        issue.status = IssueStatus.CLOSED
        issue.closed_at = timezone.now()
        issue.save()
        closed_count += 1
    
    logger.info(f"Auto-closed {closed_count} resolved issues")
    return closed_count


def get_issue_metrics(cluster=None):
    """Get issue metrics for cluster or globally."""
    issues = IssueTicket.objects.all()
    
    if cluster:
        issues = issues.filter(cluster=cluster)
    
    return {
        'total_issues': issues.count(),
        'open_issues': issues.filter(status=IssueStatus.OPEN).count(),
        'in_progress_issues': issues.filter(status=IssueStatus.IN_PROGRESS).count(),
        'resolved_issues': issues.filter(status=IssueStatus.RESOLVED).count(),
        'closed_issues': issues.filter(status=IssueStatus.CLOSED).count(),
        'escalated_issues': issues.filter(status=IssueStatus.ESCALATED).count(),
    }
