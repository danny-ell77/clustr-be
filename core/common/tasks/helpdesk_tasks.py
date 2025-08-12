"""
Scheduled tasks for helpdesk system.
"""

import logging
from celery import shared_task

from core.common.includes.helpdesk_utils import HelpdeskManager
from core.common.includes import helpdesk

logger = logging.getLogger('clustr')


@shared_task
def escalate_overdue_issues():
    """
    Scheduled task to escalate overdue issues.
    Should be run daily.
    """
    try:
        escalated_count = helpdesk.escalate_overdue_issues(days_threshold=3)
        logger.info(f"Escalated {escalated_count} overdue issues")
        return f"Escalated {escalated_count} issues"
    except Exception as e:
        logger.error(f"Error in escalate_overdue_issues task: {e}")
        raise


@shared_task
def send_due_date_reminders():
    """
    Scheduled task to send due date reminders.
    Should be run daily.
    """
    try:
        reminders_sent = helpdesk.send_due_date_reminders()
        logger.info(f"Sent {reminders_sent} due date reminders")
        return f"Sent {reminders_sent} reminders"
    except Exception as e:
        logger.error(f"Error in send_due_date_reminders task: {e}")
        raise


@shared_task
def auto_close_resolved_issues():
    """
    Scheduled task to auto-close resolved issues.
    Should be run daily.
    """
    try:
        closed_count = helpdesk.auto_close_resolved_issues(days_threshold=7)
        logger.info(f"Auto-closed {closed_count} resolved issues")
        return f"Auto-closed {closed_count} issues"
    except Exception as e:
        logger.error(f"Error in auto_close_resolved_issues task: {e}")
        raise


@shared_task
def generate_helpdesk_metrics():
    """
    Scheduled task to generate and cache helpdesk metrics.
    Should be run hourly.
    """
    try:
        from core.common.models import Cluster
        
        total_metrics = helpdesk.get_issue_metrics()
        logger.info(f"Generated global helpdesk metrics: {total_metrics}")
        
        # Generate metrics for each cluster
        clusters = Cluster.objects.all()
        for cluster in clusters:
            cluster_metrics = helpdesk.get_issue_metrics(cluster=cluster)
            logger.info(f"Generated metrics for cluster {cluster.name}: {cluster_metrics}")
        
        return "Generated helpdesk metrics successfully"
    except Exception as e:
        logger.error(f"Error in generate_helpdesk_metrics task: {e}")
        raise