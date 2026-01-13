"""
Emergencies utilities for ClustR application.
Refactored from EmergencyManager static methods to pure functions.
"""

import csv
import io
import logging
from django.db.models import Count, Avg, F
from django.db.models.functions import ExtractHour
from django.http import HttpResponse
from django.utils import timezone

from core.common.models import SOSAlert, EmergencyContact
from core.common.models.emergency import EmergencyStatus
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
        status=EmergencyStatus.ACTIVE,
    )

    logger.info(f"Emergency alert created: {alert.id} by user {user.id}")

    send_emergency_notifications(alert)

    return alert


def cancel_alert(alert, cancelled_by, reason=""):
    """Cancel an emergency alert."""
    try:
        alert.status = EmergencyStatus.CANCELLED
        alert.cancelled_by = cancelled_by
        alert.cancelled_at = timezone.now()
        alert.cancellation_reason = reason
        alert.save()

        logger.info(f"Emergency alert cancelled: {alert.id}")

        send_cancellation_notification(alert)

        return True
    except Exception as e:
        logger.error(f"Failed to cancel alert {alert.id}: {e}")
        return False


def get_user_alerts(user, **filters):
    """Get alerts for a user with optional filters."""
    return SOSAlert.objects.filter(user=user, **filters).order_by("-created_at")


def get_active_alerts(cluster):
    """Get all active alerts for a cluster."""
    return SOSAlert.objects.filter(
        cluster=cluster,
        status__in=[
            EmergencyStatus.ACTIVE,
            EmergencyStatus.ACKNOWLEDGED,
            EmergencyStatus.RESPONDING,
        ]
    ).order_by("-created_at")


def acknowledge_alert(alert, user):
    """Acknowledge an SOS alert."""
    try:
        if alert.status != EmergencyStatus.ACTIVE:
            logger.warning(f"Cannot acknowledge alert {alert.id} - not in active state")
            return False

        alert.status = EmergencyStatus.ACKNOWLEDGED
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = user
        alert.save(update_fields=["status", "acknowledged_at", "acknowledged_by"])

        logger.info(f"Alert {alert.id} acknowledged by user {user.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert.id}: {e}")
        return False


def start_response(alert, user):
    """Start response to an SOS alert."""
    try:
        if alert.status not in [EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED]:
            logger.warning(f"Cannot start response for alert {alert.id} - invalid state")
            return False

        alert.status = EmergencyStatus.RESPONDING
        alert.responded_at = timezone.now()
        alert.responded_by = user
        alert.save(update_fields=["status", "responded_at", "responded_by"])

        logger.info(f"Response started for alert {alert.id} by user {user.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start response for alert {alert.id}: {e}")
        return False


def resolve_alert(alert, user, notes=""):
    """Resolve an SOS alert."""
    try:
        if not alert.is_active:
            logger.warning(f"Cannot resolve alert {alert.id} - not active")
            return False

        alert.status = EmergencyStatus.RESOLVED
        alert.resolved_at = timezone.now()
        alert.resolved_by = user
        alert.resolution_notes = notes
        alert.save(update_fields=["status", "resolved_at", "resolved_by", "resolution_notes"])

        logger.info(f"Alert {alert.id} resolved by user {user.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert.id}: {e}")
        return False


def get_contacts_for_type(cluster, emergency_type):
    """Get emergency contacts for a specific emergency type."""
    return EmergencyContact.objects.filter(
        cluster=cluster,
        is_active=True,
        emergency_types__contains=[emergency_type]
    )


def get_statistics(cluster):
    """Get emergency statistics for a cluster."""
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)

    all_alerts = SOSAlert.objects.filter(cluster=cluster)
    recent_alerts = all_alerts.filter(created_at__gte=thirty_days_ago)

    resolved_alerts = recent_alerts.filter(
        status=EmergencyStatus.RESOLVED,
        responded_at__isnull=False
    )
    avg_response_time = None
    if resolved_alerts.exists():
        response_times = [
            (a.responded_at - a.created_at).total_seconds() / 60
            for a in resolved_alerts
            if a.responded_at
        ]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)

    type_breakdown = recent_alerts.values("emergency_type").annotate(
        count=Count("id")
    ).order_by("-count")

    status_breakdown = recent_alerts.values("status").annotate(
        count=Count("id")
    ).order_by("-count")

    return {
        "total_alerts": all_alerts.count(),
        "active_alerts": all_alerts.filter(
            status__in=[EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED, EmergencyStatus.RESPONDING]
        ).count(),
        "resolved_alerts": all_alerts.filter(status=EmergencyStatus.RESOLVED).count(),
        "cancelled_alerts": all_alerts.filter(status=EmergencyStatus.CANCELLED).count(),
        "alerts_last_30_days": recent_alerts.count(),
        "average_response_time_minutes": round(avg_response_time, 2) if avg_response_time else None,
        "by_type": list(type_breakdown),
        "by_status": list(status_breakdown),
    }


def generate_report(cluster, start_date=None, end_date=None, emergency_type=None, status=None):
    """Generate a comprehensive emergency report."""
    queryset = SOSAlert.objects.filter(cluster=cluster)

    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)
    if emergency_type:
        queryset = queryset.filter(emergency_type=emergency_type)
    if status:
        queryset = queryset.filter(status=status)

    total_alerts = queryset.count()

    resolved_with_response = queryset.filter(
        status=EmergencyStatus.RESOLVED,
        responded_at__isnull=False
    )
    avg_response_time = None
    avg_resolution_time = None

    if resolved_with_response.exists():
        response_times = [
            (a.responded_at - a.created_at).total_seconds() / 60
            for a in resolved_with_response
            if a.responded_at
        ]
        resolution_times = [
            (a.resolved_at - a.created_at).total_seconds() / 60
            for a in resolved_with_response
            if a.resolved_at
        ]

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)

    type_breakdown = queryset.values("emergency_type").annotate(
        count=Count("id")
    ).order_by("-count")

    status_breakdown = queryset.values("status").annotate(
        count=Count("id")
    ).order_by("-count")

    priority_breakdown = queryset.values("priority").annotate(
        count=Count("id")
    ).order_by("-count")

    alerts_data = list(queryset.values(
        "alert_id", "emergency_type", "status", "priority",
        "location", "created_at", "resolved_at", "user__first_name", "user__last_name"
    ).order_by("-created_at")[:100])

    return {
        "start_date": start_date,
        "end_date": end_date,
        "filters": {
            "emergency_type": emergency_type,
            "status": status,
        },
        "summary": {
            "total_alerts": total_alerts,
            "active_count": queryset.filter(
                status__in=[EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED, EmergencyStatus.RESPONDING]
            ).count(),
            "resolved_count": queryset.filter(status=EmergencyStatus.RESOLVED).count(),
            "cancelled_count": queryset.filter(status=EmergencyStatus.CANCELLED).count(),
            "average_response_time_minutes": round(avg_response_time, 2) if avg_response_time else None,
            "average_resolution_time_minutes": round(avg_resolution_time, 2) if avg_resolution_time else None,
        },
        "by_type": list(type_breakdown),
        "by_status": list(status_breakdown),
        "by_priority": list(priority_breakdown),
        "alerts": alerts_data,
    }


def generate_incident_report(alert):
    """Generate an incident report for an alert."""
    return {
        "alert_id": str(alert.id),
        "alert_number": alert.alert_id,
        "user": f"{alert.user.first_name} {alert.user.last_name}",
        "user_id": str(alert.user.id),
        "emergency_type": alert.emergency_type,
        "location": alert.location,
        "description": alert.description,
        "priority": alert.priority,
        "status": alert.status,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "acknowledged_by": f"{alert.acknowledged_by.first_name} {alert.acknowledged_by.last_name}" if alert.acknowledged_by else None,
        "responded_at": alert.responded_at,
        "responded_by": f"{alert.responded_by.first_name} {alert.responded_by.last_name}" if alert.responded_by else None,
        "resolved_at": alert.resolved_at,
        "resolved_by": f"{alert.resolved_by.first_name} {alert.resolved_by.last_name}" if alert.resolved_by else None,
        "resolution_notes": alert.resolution_notes,
        "response_time_minutes": alert.response_time_minutes,
        "resolution_time_minutes": alert.resolution_time_minutes,
    }


def export_report_as_csv(report):
    """Export emergency report as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Emergency Report"])
    writer.writerow([])

    writer.writerow(["Summary"])
    summary = report.get("summary", {})
    writer.writerow(["Total Alerts", summary.get("total_alerts", 0)])
    writer.writerow(["Active", summary.get("active_count", 0)])
    writer.writerow(["Resolved", summary.get("resolved_count", 0)])
    writer.writerow(["Cancelled", summary.get("cancelled_count", 0)])
    writer.writerow(["Avg Response Time (min)", summary.get("average_response_time_minutes", "N/A")])
    writer.writerow(["Avg Resolution Time (min)", summary.get("average_resolution_time_minutes", "N/A")])
    writer.writerow([])

    writer.writerow(["Alert ID", "Type", "Status", "Priority", "Location", "Created At", "User"])
    for alert in report.get("alerts", []):
        writer.writerow([
            alert.get("alert_id"),
            alert.get("emergency_type"),
            alert.get("status"),
            alert.get("priority"),
            alert.get("location"),
            alert.get("created_at"),
            f"{alert.get('user__first_name', '')} {alert.get('user__last_name', '')}".strip(),
        ])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="emergency_report.csv"'
    return response


def export_report_as_pdf(report):
    """Export emergency report as PDF (simple text format as placeholder)."""
    content = "Emergency Report\n"
    content += "=" * 50 + "\n\n"

    summary = report.get("summary", {})
    content += "Summary\n"
    content += "-" * 30 + "\n"
    content += f"Total Alerts: {summary.get('total_alerts', 0)}\n"
    content += f"Active: {summary.get('active_count', 0)}\n"
    content += f"Resolved: {summary.get('resolved_count', 0)}\n"
    content += f"Cancelled: {summary.get('cancelled_count', 0)}\n"
    content += f"Avg Response Time: {summary.get('average_response_time_minutes', 'N/A')} min\n"
    content += f"Avg Resolution Time: {summary.get('average_resolution_time_minutes', 'N/A')} min\n\n"

    content += "Alerts\n"
    content += "-" * 30 + "\n"
    for alert in report.get("alerts", [])[:50]:
        user_name = f"{alert.get('user__first_name', '')} {alert.get('user__last_name', '')}".strip()
        content += f"- {alert.get('alert_id')}: {alert.get('emergency_type')} ({alert.get('status')}) - {user_name}\n"

    response = HttpResponse(content, content_type="text/plain")
    response["Content-Disposition"] = 'attachment; filename="emergency_report.txt"'
    return response


def send_emergency_notifications(alert):
    """Send emergency notifications to contacts."""
    try:
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
                    "user_name": f"{alert.user.first_name} {alert.user.last_name}",
                    "emergency_type": alert.emergency_type,
                    "location": alert.location,
                    "description": alert.description,
                    "severity": getattr(alert, 'severity', 'medium'),
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
                    "user_name": f"{alert.user.first_name} {alert.user.last_name}",
                    "cancellation_reason": alert.cancellation_reason,
                    "cancelled_at": alert.cancelled_at.strftime("%Y-%m-%d %H:%M"),
                },
            )

        return True
    except Exception as e:
        logger.error(f"Failed to send cancellation notification: {e}")
        return False

