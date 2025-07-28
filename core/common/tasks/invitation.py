
import logging
from celery import shared_task
from django.utils import timezone

from core.common.models import Invitation

logger = logging.getLogger(__name__)


@shared_task(name="update_invitation_statuses")
def update_invitation_statuses():
    """
    Updates invitation statuses based on their start and end dates.
    This task should be called periodically by a scheduler.
    """
    current_date = timezone.now().date()
    
    expired_invitations = Invitation.objects.filter(
        status=Invitation.Status.ACTIVE,
        end_date__lt=current_date
    )
    
    expired_count = expired_invitations.update(status=Invitation.Status.EXPIRED)
    
    if expired_count > 0:
        logger.info(f"Updated {expired_count} invitations to EXPIRED status")
    
    logger.info("Checking for recurring invitations that need to be reactivated")
