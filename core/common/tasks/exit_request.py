
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from core.common.models import ExitRequest

logger = logging.getLogger(__name__)


@shared_task(name="expire_old_exit_requests")
def expire_old_exit_requests():
    """
    Marks expired exit requests as expired.
    This task should be called periodically by a scheduler.
    """
    try:
        current_time = timezone.now()
        expired_requests = ExitRequest.objects.filter(
            status=ExitRequest.Status.PENDING,
            expires_at__lt=current_time
        )
        expired_count = expired_requests.update(status=ExitRequest.Status.EXPIRED)
        
        if expired_count > 0:
            logger.info(f"Marked {expired_count} exit requests as expired")
            
    except Exception as e:
        logger.error(f"Error expiring old exit requests: {str(e)}")


@shared_task(name="send_exit_request_reminders")
def send_exit_request_reminders():
    """
    Sends reminders for pending exit requests that are about to expire.
    This task should be called periodically by a scheduler.
    """
    try:
        reminder_threshold = timezone.now() + timedelta(hours=2)
        pending_requests = ExitRequest.objects.filter(
            status=ExitRequest.Status.PENDING,
            expires_at__lt=reminder_threshold,
            expires_at__gt=timezone.now()
        ).iterator()
        
        reminder_count = 0
        for request in pending_requests:
            try:
                # TODO: Implement actual reminder notification sending
                # NotificationManager.send_exit_request_reminder(request)
                reminder_count += 1
                logger.info(f"Sent reminder for exit request: {request.request_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for exit request {request.request_id}: {str(e)}")
        
        if reminder_count > 0:
            logger.info(f"Sent {reminder_count} exit request reminders")
            
    except Exception as e:
        logger.error(f"Error sending exit request reminders: {str(e)}")
