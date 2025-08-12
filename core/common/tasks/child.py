
import logging
from celery import shared_task
from django.utils import timezone

from core.common.models import EntryExitLog
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

logger = logging.getLogger(__name__)


@shared_task(name="check_overdue_children")
def check_overdue_children():
    """
    Checks for children who are overdue for return and sends alerts.
    This task should be called periodically by a scheduler.
    """
    try:
        current_time = timezone.now()
        overdue_logs = EntryExitLog.objects.filter(
            log_type=EntryExitLog.LogType.EXIT,
            status=EntryExitLog.Status.IN_PROGRESS,
            expected_return_time__lt=current_time
        ).iterator()
        
        overdue_count = 0
        for log in overdue_logs:
            if log.mark_overdue():
                overdue_count += 1
                try:
                    recipients = []
                    if log.child.parent:
                        recipients.append(log.child.parent)
                    
                    notifications.send(
                        event=NotificationEvents.CHILD_OVERDUE_ALERT,
                        recipients=recipients,
                        cluster=log.cluster,
                        context={
                            "child_name": log.child.name,
                            "parent_name": log.child.parent.name if log.child.parent else "N/A",
                            "expected_return_time": log.expected_return_time.strftime("%Y-%m-%d %H:%M"),
                            "overdue_minutes": int((timezone.now() - log.expected_return_time).total_seconds() / 60),
                            "destination": log.destination,
                            "accompanying_adult": log.accompanying_adult,
                            "parent_phone": log.child.parent.phone_number if log.child.parent else "N/A",
                        }
                    )
                    logger.info(f"Sent overdue notification for child: {log.child.name} (ID: {log.child.id})")
                except Exception as e:
                    logger.error(f"Failed to send overdue notification for child {log.child.name}: {str(e)}")
        
        if overdue_count > 0:
            logger.info(f"Marked {overdue_count} children as overdue")
            
    except Exception as e:
        logger.error(f"Error checking overdue children: {str(e)}")
