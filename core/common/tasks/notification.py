"""
Celery tasks for notification management.

This module contains Celery tasks for sending notifications asynchronously.
"""

import logging
from typing import List, Any, Dict
from celery import shared_task
from django.contrib.auth import get_user_model

from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager
from core.common.models.cluster import Cluster

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(name="send_notification")
def send_notification_task(
    event_name: str,
    recipient_ids: List[str],
    cluster_id: str,
    context: Dict[str, Any],
) -> bool:
    """
    Celery task to send notifications asynchronously.

    This task handles the actual sending of notifications in the background.
    It deserializes the input data and calls the NotificationManager's internal
    sending method.

    Args:
        event_name: String representation of the notification event
        recipient_ids: List of user IDs to notify
        cluster_id: ID of the cluster context
        context: Context data for the notification

    Returns:
        True if all notifications sent successfully, False otherwise
    """
    try:
        # Convert string event name back to enum
        event_enum = NotificationEvents(event_name)

        # Get cluster instance
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            logger.error(f"Cluster not found: {cluster_id}")
            return False

        recipients = User.objects.filter(cluster_id=cluster_id, pk__in=recipient_ids)

        if not recipients:
            logger.warning(f"No valid recipients found for event: {event_name}")
            return True  # Not an error if no recipients

        # Call the internal sending method
        for batch in recipients.iterator(chunk_size=100):
            NotificationManager._send_notification_internal(
                event_name=event_enum,
                recipients=list(batch),
                cluster=cluster,
                context=context,
            )

        logger.info(
            f"Notification task completed for event {event_name}: "
            f"{len(recipients)} recipients, cluster {cluster.name}, result: {result}"
        )

        return result

    except Exception as e:
        logger.error(f"Error in notification task for event {event_name}: {str(e)}")
        return False


@shared_task(name="send_notification_with_retry")
def send_notification_with_retry_task(
    event_name: str,
    recipient_ids: List[str],
    cluster_id: str,
    context: Dict[str, Any],
    max_retries: int = 3,
) -> bool:
    """
    Celery task to send notifications with retry logic.

    This task includes automatic retry functionality for failed notifications.

    Args:
        event_name: String representation of the notification event
        recipient_ids: List of user IDs to notify
        cluster_id: ID of the cluster context
        context: Context data for the notification
        max_retries: Maximum number of retry attempts

    Returns:
        True if all notifications sent successfully, False otherwise
    """
    try:
        result = send_notification_task.apply_async(
            args=[event_name, recipient_ids, cluster_id, context],
            retry=True,
            retry_policy={
                "max_retries": max_retries,
                "interval_start": 0,
                "interval_step": 0.2,
                "interval_max": 0.2,
            },
        )
        return result.get()
    except Exception as e:
        logger.error(
            f"Error in retry notification task for event {event_name}: {str(e)}"
        )
        return False
