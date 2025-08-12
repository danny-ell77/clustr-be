"""
Emergencies utilities for ClustR application.
Refactored from EmergencyManager static methods to pure functions.
"""

import logging
from django.utils import timezone

from core.common.models import SOSAlert, EmergencyContact
from core.common.includes import notifications
from core.notifications.events import NotificationEvents

logger = logging.getLogger("clustr")


def create_alert(user, emergency_type, location="", description="", severity="medium"):
    """Create an SOS alert."""
    alert = SOSAlert.objects.create(
        cluster=user.cluster,
        user=user,
        emergency_type=emergency_type,
        location=location,
        description=description,
        severity=severity,
        status="active",
    )

    logger.info(f"Emergency alert created: {alert.id} by user {user.id}")

    # Send immediate notifications to emergency contacts
    send_emergency_notifications(alert)

    return alert


def cancel_alert(alert, cancelled_by, reason=""):
    """Cancel an emergency alert."""
    try:
        alert.status = "cancelled"
        alert.cancelled_by = cancelled_by
        alert.cancelled_at = timezone.now()
        alert.cancellation_reason = reason
        alert.save()

        logger.info(f"Emergency alert cancelled: {alert.id}")

        # Send cancellation notification
        send_cancellation_notification(alert)

        return True
    except Exception as e:
        logger.error(f"Failed to cancel alert {alert.id}: {e}")
        return False


def get_user_alerts(user, **filters):
    """Get alerts for a user with optional filters."""
    return SOSAlert.objects.filter(user=user, **filters).order_by("-created_at")


def generate_incident_report(alert):
    """Generate an incident report for an alert."""
    return {
        "alert_id": alert.id,
        "user": alert.user.name,
        "emergency_type": alert.emergency_type,
        "location": alert.location,
        "description": alert.description,
        "severity": alert.severity,
        "created_at": alert.created_at,
        "status": alert.status,
        "response_time": (
            alert.response_time if hasattr(alert, "response_time") else None
        ),
        "resolved_at": alert.resolved_at if hasattr(alert, "resolved_at") else None,
    }


# Notification helper functions
def send_emergency_notifications(alert):
    """Send emergency notifications to contacts."""
    try:
        # Get emergency contacts for the cluster
        contacts = EmergencyContact.objects.filter(
            cluster=alert.cluster, is_active=True
        )

        if contacts:
            notifications.send(
                event_name=NotificationEvents.EMERGENCY_ALERT,
                recipients=list(contacts),
                cluster=alert.cluster,
                context={
                    "alert_id": alert.id,
                    "user_name": alert.user.name,
                    "emergency_type": alert.emergency_type,
                    "location": alert.location,
                    "description": alert.description,
                    "severity": alert.severity,
                    "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M"),
                },
            )

        return True
    except Exception as e:
        logger.error(f"Failed to send emergency notifications: {e}")
        return False


def send_cancellation_notification(alert):
    """Send alert cancellation notification."""
    try:
        contacts = EmergencyContact.objects.filter(
            cluster=alert.cluster, is_active=True
        )

        if contacts:
            notifications.send(
                event_name=NotificationEvents.EMERGENCY_CANCELLED,
                recipients=list(contacts),
                cluster=alert.cluster,
                context={
                    "alert_id": alert.id,
                    "user_name": alert.user.name,
                    "cancellation_reason": alert.cancellation_reason,
                    "cancelled_at": alert.cancelled_at.strftime("%Y-%m-%d %H:%M"),
                },
            )

        return True
    except Exception as e:
        logger.error(f"Failed to send cancellation notification: {e}")
        return False
