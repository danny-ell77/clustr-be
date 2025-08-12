import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from accounts.models import AccountUser
from core.common.models import Visitor
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

logger = logging.getLogger(__name__)


@shared_task(name="detect_visitor_overstays")
def detect_visitor_overstays():
    """
    Detects visitors who have overstayed their scheduled visit duration.
    This task should be called periodically by a scheduler.
    """
    current_time = timezone.now()
    grace_period = timedelta(hours=2)

    overstaying_visitors = Visitor.objects.filter(
        status=Visitor.Status.CHECKED_IN,
        estimated_arrival__lt=current_time - grace_period,
    ).iterator()

    for visitor in overstaying_visitors:
        logger.info(f"Detected overstaying visitor: {visitor.name} (ID: {visitor.id})")

        try:
            try:
                user = AccountUser.objects.get(id=visitor.user_id)
            except AccountUser.DoesNotExist:
                logger.error(
                    f"User not found for visitor: {visitor.name} (ID: {visitor.id})"
                )
                continue

            # Use the new async notification approach
            success = notifications.send(
                event_name=NotificationEvents.VISITOR_OVERSTAY,
                recipients=[user],
                cluster=visitor.cluster,
                context={
                    "visitor_name": visitor.name,
                    "access_code": visitor.access_code,
                },
            )

            if success:
                logger.info(
                    f"Overstay notification dispatched for visitor: {visitor.name} (ID: {visitor.id})"
                )
            else:
                logger.error(
                    f"Failed to dispatch overstay notification for visitor: {visitor.name} (ID: {visitor.id})"
                )

        except Exception as e:
            logger.error(
                f"Failed to process overstay notification for {visitor.name}: {str(e)}"
            )
