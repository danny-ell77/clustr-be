
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from core.common.includes import notifications

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
                # Send exit request reminder notification
                success = send_exit_request_reminder(request)
                if success:
                    reminder_count += 1
                    logger.info(f"Sent reminder for exit request: {request.request_id}")
                else:
                    logger.error(f"Failed to send reminder for exit request {request.request_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for exit request {request.request_id}: {str(e)}")
        
        if reminder_count > 0:
            logger.info(f"Sent {reminder_count} exit request reminders")
            
    except Exception as e:
        logger.error(f"Error sending exit request reminders: {str(e)}")


def send_exit_request_reminder(exit_request):
    """
    Send reminder notification for an exit request that's about to expire.
    
    Args:
        exit_request: ExitRequest object
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        from core.notifications.events import NotificationEvents
        from accounts.models import AccountUser
        
        # Get the user who made the exit request
        try:
            user = AccountUser.objects.get(id=exit_request.user_id)
        except AccountUser.DoesNotExist:
            logger.error(f"User not found for exit request: {exit_request.request_id}")
            return False
        
        # Calculate time until expiration
        time_until_expiry = exit_request.expires_at - timezone.now()
        hours_until_expiry = int(time_until_expiry.total_seconds() / 3600)
        minutes_until_expiry = int((time_until_expiry.total_seconds() % 3600) / 60)
        
        # Format time remaining
        if hours_until_expiry > 0:
            time_remaining = f"{hours_until_expiry} hour{'s' if hours_until_expiry != 1 else ''}"
            if minutes_until_expiry > 0:
                time_remaining += f" and {minutes_until_expiry} minute{'s' if minutes_until_expiry != 1 else ''}"
        else:
            time_remaining = f"{minutes_until_expiry} minute{'s' if minutes_until_expiry != 1 else ''}"
        
        # Send notification
        notifications.send(
            event_name=NotificationEvents.EXIT_REQUEST_REMINDER,
            recipients=[user],
            cluster=exit_request.cluster,
            context={
                'request_id': exit_request.request_id,
                'child_name': exit_request.child.name if exit_request.child else 'Unknown',
                'exit_date': exit_request.exit_date.strftime('%Y-%m-%d') if exit_request.exit_date else 'Not specified',
                'exit_time': exit_request.exit_time.strftime('%H:%M') if exit_request.exit_time else 'Not specified',
                'expires_at': exit_request.expires_at.strftime('%Y-%m-%d %H:%M'),
                'time_remaining': time_remaining,
                'destination': exit_request.destination or 'Not specified',
                'reason': exit_request.reason or 'Not specified',
                'guardian_name': exit_request.guardian_name or user.name,
                'guardian_phone': exit_request.guardian_phone or user.phone_number,
            }
        )
        
        logger.info(f"Exit request reminder sent for request {exit_request.request_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send exit request reminder for {exit_request.request_id}: {e}")
        return False