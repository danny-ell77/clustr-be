"""
Example demonstrating the new Celery-based notification system.

This example shows how to use the different notification methods:
- send(): Asynchronous sending via Celery (default)
- send_sync(): Synchronous sending for critical events
- send_with_retry(): Asynchronous sending with retry logic
- send_bulk(): Bulk notification sending
"""

import logging
from django.contrib.auth import get_user_model
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager
from core.common.models.cluster import Cluster

User = get_user_model()
logger = logging.getLogger(__name__)


def example_async_notification():
    """
    Example of sending a notification asynchronously (default behavior).
    """
    try:
        # Get a user and cluster (in real usage, these would come from your application)
        user = User.objects.first()
        cluster = Cluster.objects.first()

        if not user or not cluster:
            logger.warning("No user or cluster found for example")
            return

        # Send notification asynchronously (dispatches Celery task)
        success = NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[user],
            cluster=cluster,
            context={
                "visitor_name": "John Doe",
                "unit": "A101",
                "arrival_time": "14:30",
            },
        )

        if success:
            logger.info("Notification task dispatched successfully")
        else:
            logger.error("Failed to dispatch notification task")

    except Exception as e:
        logger.error(f"Error in async notification example: {str(e)}")


def example_sync_notification():
    """
    Example of sending a notification synchronously (for critical events).
    """
    try:
        user = User.objects.first()
        cluster = Cluster.objects.first()

        if not user or not cluster:
            logger.warning("No user or cluster found for example")
            return

        # Send notification synchronously (immediate delivery)
        success = NotificationManager.send_sync(
            event_name=NotificationEvents.EMERGENCY_ALERT,
            recipients=[user],
            cluster=cluster,
            context={
                "severity": "HIGH",
                "message": "Fire alarm activated",
                "location": "Building A",
            },
        )

        if success:
            logger.info("Critical notification sent synchronously")
        else:
            logger.error("Failed to send critical notification")

    except Exception as e:
        logger.error(f"Error in sync notification example: {str(e)}")


def example_retry_notification():
    """
    Example of sending a notification with retry logic.
    """
    try:
        user = User.objects.first()
        cluster = Cluster.objects.first()

        if not user or not cluster:
            logger.warning("No user or cluster found for example")
            return

        # Send notification with retry logic
        success = NotificationManager.send_with_retry(
            event_name=NotificationEvents.PAYMENT_OVERDUE,
            recipients=[user],
            cluster=cluster,
            context={
                "amount": 150.00,
                "due_date": "2024-01-15",
                "bill_type": "Maintenance",
            },
            max_retries=5,
        )

        if success:
            logger.info("Retry notification task dispatched successfully")
        else:
            logger.error("Failed to dispatch retry notification task")

    except Exception as e:
        logger.error(f"Error in retry notification example: {str(e)}")


def example_bulk_notifications():
    """
    Example of sending multiple notifications in bulk.
    """
    try:
        users = list(User.objects.all()[:5])  # Get first 5 users
        cluster = Cluster.objects.first()

        if not users or not cluster:
            logger.warning("No users or cluster found for example")
            return

        # Prepare bulk notifications
        notifications = []

        for i, user in enumerate(users):
            notifications.append(
                {
                    "event_name": NotificationEvents.ANNOUNCEMENT,
                    "recipients": [user],
                    "cluster": cluster,
                    "context": {
                        "title": f"Announcement {i+1}",
                        "message": f"This is announcement number {i+1}",
                        "priority": "normal",
                    },
                }
            )

        # Send bulk notifications
        results = NotificationManager.send_bulk(notifications)

        successful_count = sum(1 for success in results.values() if success)
        logger.info(
            f"Bulk notification completed: {successful_count}/{len(results)} successful"
        )

    except Exception as e:
        logger.error(f"Error in bulk notification example: {str(e)}")


def example_critical_event_handling():
    """
    Example showing how critical events are handled automatically.
    """
    try:
        user = User.objects.first()
        cluster = Cluster.objects.first()

        if not user or not cluster:
            logger.warning("No user or cluster found for example")
            return

        # Critical events (like emergency alerts) are sent synchronously automatically
        success = NotificationManager.send(
            event_name=NotificationEvents.EMERGENCY_ALERT,
            recipients=[user],
            cluster=cluster,
            context={
                "severity": "CRITICAL",
                "message": "Security breach detected",
                "location": "Main gate",
            },
        )

        # The manager automatically detects this is a critical event and sends it synchronously
        if success:
            logger.info("Critical event notification sent (automatically synchronous)")
        else:
            logger.error("Failed to send critical event notification")

    except Exception as e:
        logger.error(f"Error in critical event example: {str(e)}")


if __name__ == "__main__":
    # Run examples
    print("Running notification examples...")

    example_async_notification()
    example_sync_notification()
    example_retry_notification()
    example_bulk_notifications()
    example_critical_event_handling()

    print("Notification examples completed!")
