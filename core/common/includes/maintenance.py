"""
Maintenance utilities for ClustR application.
Refactored from MaintenanceManager static methods to pure functions.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db import models

from core.common.includes import notifications
from core.notifications.events import NotificationEvents
from core.common.models import (
    MaintenanceLog,
    MaintenanceAttachment,
    MaintenanceStatus,
)
from core.common.includes.file_storage import FileStorage

logger = logging.getLogger("clustr")


def create_log(cluster, requested_by, title, description, priority="medium", **kwargs):
    """Create a maintenance log entry."""
    maintenance_log = MaintenanceLog.objects.create(
        cluster=cluster,
        requested_by=requested_by,
        title=title,
        description=description,
        priority=priority,
        status="pending",
        **kwargs,
    )

    logger.info(
        f"Maintenance log created: {maintenance_log.id} by user {requested_by.id}"
    )
    return maintenance_log


def upload_attachment(
    maintenance_log, file_obj, uploaded_by, attachment_type="general"
):
    """Upload an attachment for a maintenance log."""
    try:
        # Use FileStorage to handle the upload
        file_url = FileStorage.upload_file(
            file_obj,
            folder=f"maintenance/{maintenance_log.id}",
            allowed_extensions=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
        )

        attachment = MaintenanceAttachment.objects.create(
            maintenance_log=maintenance_log,
            file_url=file_url,
            file_name=file_obj.name,
            file_size=file_obj.size,
            attachment_type=attachment_type,
            uploaded_by=uploaded_by,
        )

        logger.info(f"Maintenance attachment uploaded: {attachment.id}")
        return attachment

    except Exception as e:
        logger.error(f"Failed to upload maintenance attachment: {e}")
        raise


def update_status(maintenance_log, new_status, updated_by, notes=""):
    """Update maintenance log status."""
    try:
        old_status = maintenance_log.status
        maintenance_log.status = new_status
        maintenance_log.last_updated_by = updated_by
        maintenance_log.last_updated_at = timezone.now()

        if notes:
            maintenance_log.notes = notes

        maintenance_log.save()

        logger.info(
            f"Maintenance log {maintenance_log.id} status updated from {old_status} to {new_status}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to update maintenance log status: {e}")
        return False


def assign_log(maintenance_log, assigned_to, assigned_by):
    """Assign maintenance log to a staff member."""
    try:
        maintenance_log.performed_by = assigned_to
        maintenance_log.last_modified_by = assigned_by.id
        maintenance_log.save()

        logger.info(
            f"Maintenance log {maintenance_log.id} assigned to {assigned_to.name}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to assign maintenance log: {e}")
        return False


def get_history(
    cluster, property_location=None, equipment_name=None, property_type=None, limit=None
):
    """Get maintenance history with optional filtering."""
    logs = MaintenanceLog.objects.filter(cluster=cluster)

    if property_location:
        logs = logs.filter(property_location__icontains=property_location)
    if equipment_name:
        logs = logs.filter(equipment_name__icontains=equipment_name)
    if property_type:
        logs = logs.filter(property_type=property_type)

    logs = logs.order_by("-created_at")

    if limit:
        logs = logs[:limit]

    return logs


def get_analytics(cluster, start_date=None, end_date=None):
    """Get maintenance analytics and statistics."""
    logs = MaintenanceLog.objects.filter(cluster=cluster)

    if start_date:
        logs = logs.filter(created_at__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__lte=end_date)

    return {
        "total_maintenance": logs.count(),
        "completed": logs.filter(status="COMPLETED").count(),
        "in_progress": logs.filter(status="IN_PROGRESS").count(),
        "scheduled": logs.filter(status="SCHEDULED").count(),
        "cancelled": logs.filter(status="CANCELLED").count(),
        "by_type": {
            "preventive": logs.filter(maintenance_type="PREVENTIVE").count(),
            "corrective": logs.filter(maintenance_type="CORRECTIVE").count(),
            "emergency": logs.filter(maintenance_type="EMERGENCY").count(),
            "routine": logs.filter(maintenance_type="ROUTINE").count(),
        },
        "by_priority": {
            "urgent": logs.filter(priority="URGENT").count(),
            "high": logs.filter(priority="HIGH").count(),
            "medium": logs.filter(priority="MEDIUM").count(),
            "low": logs.filter(priority="LOW").count(),
        },
    }


def suggest_optimizations(cluster):
    """Get maintenance optimization suggestions."""
    logs = MaintenanceLog.objects.filter(cluster=cluster)
    suggestions = []

    # Check for frequently maintained items
    frequent_items = (
        logs.values("equipment_name")
        .annotate(count=models.Count("id"))
        .filter(count__gte=5)
        .order_by("-count")
    )

    for item in frequent_items[:5]:
        suggestions.append(
            {
                "type": "frequent_maintenance",
                "title": f'High maintenance frequency for {item["equipment_name"]}',
                "description": f'This equipment has required maintenance {item["count"]} times. Consider upgrade or replacement.',
                "priority": "medium",
            }
        )

    # Check for overdue maintenance
    overdue = logs.filter(
        scheduled_date__lt=timezone.now(), status__in=["SCHEDULED", "POSTPONED"]
    ).count()

    if overdue > 0:
        suggestions.append(
            {
                "type": "overdue_maintenance",
                "title": f"{overdue} overdue maintenance items",
                "description": "Schedule resources to complete overdue maintenance tasks.",
                "priority": "high",
            }
        )

    return suggestions


def create_schedule(cluster, created_by, **kwargs):
    """Create a maintenance schedule."""
    from core.common.models import MaintenanceSchedule

    schedule = MaintenanceSchedule.objects.create(
        cluster=cluster, created_by=created_by.id, **kwargs
    )

    logger.info(f"Maintenance schedule created: {schedule.id}")
    return schedule


def get_by_category(cluster, property_type=None, maintenance_type=None):
    """Get maintenance by category."""
    logs = MaintenanceLog.objects.filter(cluster=cluster)

    if property_type:
        logs = logs.filter(property_type=property_type)
    if maintenance_type:
        logs = logs.filter(maintenance_type=maintenance_type)

    categories = {}
    for log in logs:
        category_key = f"{log.property_type}_{log.maintenance_type}"
        if category_key not in categories:
            categories[category_key] = {
                "property_type": log.property_type,
                "maintenance_type": log.maintenance_type,
                "count": 0,
                "logs": [],
            }
        categories[category_key]["count"] += 1
        categories[category_key]["logs"].append(
            {
                "id": log.id,
                "title": log.title,
                "status": log.status,
                "created_at": log.created_at,
            }
        )
    return list(categories.values())


def send_completion_notification(maintenance_log, completed_by):
    """Send maintenance completion notification."""
    try:
        from core.common.includes import notifications
        from core.notifications.events import NotificationEvents

        # Notify the requester
        if maintenance_log.requested_by:
            notifications.send(
                event_name=NotificationEvents.MAINTENANCE_COMPLETED,
                recipients=[maintenance_log.requested_by],
                cluster=maintenance_log.cluster,
                context={
                    "maintenance_title": maintenance_log.title,
                    "maintenance_number": maintenance_log.maintenance_number,
                    "completed_by": completed_by.name,
                    "completion_notes": maintenance_log.completion_notes,
                    "completed_at": maintenance_log.completed_at.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                },
            )

        logger.info(
            f"Completion notification sent for maintenance {maintenance_log.id}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")
        return False


def get_logs_summary(cluster, user=None):
    """Get maintenance logs summary."""
    logs = MaintenanceLog.objects.filter(cluster=cluster)

    if user:
        logs = logs.filter(requested_by=user)

    return {
        "total_logs": logs.count(),
        "pending_logs": logs.filter(status="pending").count(),
        "in_progress_logs": logs.filter(status="in_progress").count(),
        "completed_logs": logs.filter(status="completed").count(),
        "cancelled_logs": logs.filter(status="cancelled").count(),
    }


def process_due_schedules(cluster):
    """Process due maintenance schedules and create maintenance logs."""
    from django.utils import timezone
    from core.common.models import MaintenanceSchedule

    now = timezone.now()
    due_schedules = MaintenanceSchedule.objects.filter(
        cluster=cluster, is_active=True, next_due_date__lte=now
    )

    created_logs = []
    for schedule in due_schedules:
        try:
            # Create maintenance log from schedule
            log = create_log(
                cluster=cluster,
                requested_by=None,  # System generated
                title=f"Scheduled: {schedule.name}",
                description=f"Scheduled maintenance for {schedule.property_location}",
                priority=schedule.priority or "MEDIUM",
                property_location=schedule.property_location,
                equipment_name=schedule.equipment_name,
                maintenance_type="PREVENTIVE",
                scheduled_date=schedule.next_due_date,
            )

            # Update schedule's next due date
            schedule.update_next_due_date()
            created_logs.append(log)

        except Exception as e:
            logger.error(
                f"Failed to create maintenance log from schedule {schedule.id}: {e}"
            )

    logger.info(f"Created {len(created_logs)} maintenance logs from schedules")
    return created_logs


def send_due_alerts(cluster):
    """Send alerts for maintenance that is due soon."""

    now = timezone.now()
    due_soon = now + timedelta(hours=24)

    due_maintenance = MaintenanceLog.objects.filter(
        cluster=cluster,
        status__in=[MaintenanceLogStatus.SCHEDULED],
        scheduled_date__gte=now,
        scheduled_date__lte=due_soon,
        performed_by__isnull=False,
    )

    count = 0
    for maintenance in due_maintenance:
        try:
            if maintenance.performed_by:
                notifications.send(
                    event_name=NotificationEvents.MAINTENANCE_DUE,
                    recipients=[maintenance.performed_by],
                    cluster=cluster,
                    context={
                        "maintenance_title": maintenance.title,
                        "maintenance_number": maintenance.maintenance_number,
                        "due_date": maintenance.scheduled_date.strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "location": maintenance.property_location,
                        "priority": maintenance.priority,
                    },
                )
                count += 1
        except Exception as e:
            logger.error(
                f"Failed to send maintenance due alert for {maintenance.id}: {e}"
            )

    logger.info(f"Sent {count} maintenance due alerts")
    return count
