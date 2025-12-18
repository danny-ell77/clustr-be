"""
Shifts utilities for ClustR application.
Refactored from ShiftManager static methods to pure functions.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.exceptions import ValidationError

from core.common.models import Shift, ShiftAttendance, ShiftSwapRequest, ShiftStatus
from core.common.includes import notifications
from core.notifications.events import NotificationEvents

logger = logging.getLogger('clustr')


def create(cluster, title, shift_type, assigned_staff, start_time, end_time, **kwargs):
    """Create a new shift with conflict detection."""
    # Check for overlapping shifts
    conflicts = check_conflicts(cluster, assigned_staff, start_time, end_time)
    
    if conflicts:
        conflict_details = [
            f"{shift.title} ({shift.start_time.strftime('%Y-%m-%d %H:%M')} - {shift.end_time.strftime('%H:%M')})"
            for shift in conflicts
        ]
        raise ValidationError(f"Shift conflicts detected: {', '.join(conflict_details)}")
    
    shift = Shift.objects.create(
        cluster=cluster,
        title=title,
        shift_type=shift_type,
        assigned_staff=assigned_staff,
        start_time=start_time,
        end_time=end_time,
        **kwargs
    )
    
    logger.info(f"Shift created: {shift.id} for {assigned_staff.name}")
    return shift


def check_conflicts(cluster, staff_member, start_time, end_time, exclude_shift_id=None):
    """Check for shift conflicts for a staff member."""
    conflicts = Shift.objects.filter(
        cluster=cluster,
        assigned_staff=staff_member,
        start_time__lt=end_time,
        end_time__gt=start_time,
        status__in=[ShiftStatus.SCHEDULED, ShiftStatus.IN_PROGRESS]
    )
    
    if exclude_shift_id:
        conflicts = conflicts.exclude(id=exclude_shift_id)
    
    return list(conflicts)


def clock_in(shift, clock_in_time=None):
    """Clock in staff for a shift."""
    if not clock_in_time:
        clock_in_time = timezone.now()
    
    shift.actual_start_time = clock_in_time
    shift.status = ShiftStatus.IN_PROGRESS
    shift.save()
    
    logger.info(f"Staff clocked in for shift {shift.id}")
    return shift


def clock_out(shift, clock_out_time=None):
    """Clock out staff from a shift."""
    if not clock_out_time:
        clock_out_time = timezone.now()
    
    shift.actual_end_time = clock_out_time
    shift.status = ShiftStatus.COMPLETED
    shift.save()
    
    logger.info(f"Staff clocked out from shift {shift.id}")
    return shift


def get_statistics(cluster, start_date=None, end_date=None):
    """Get shift statistics for a cluster."""
    shifts = Shift.objects.filter(cluster=cluster)
    
    if start_date:
        shifts = shifts.filter(start_time__gte=start_date)
    if end_date:
        shifts = shifts.filter(end_time__lte=end_date)
    
    return {
        'total_shifts': shifts.count(),
        'completed_shifts': shifts.filter(status=ShiftStatus.COMPLETED).count(),
        'missed_shifts': shifts.filter(status=ShiftStatus.NO_SHOW).count(),
        'in_progress_shifts': shifts.filter(status=ShiftStatus.IN_PROGRESS).count(),
    }


def create_swap_request(original_shift_id, requested_by, requested_shift_id=None, reason=""):
    """Create a shift swap request."""
    swap_request = ShiftSwapRequest.objects.create(
        original_shift_id=original_shift_id,
        requested_by=requested_by,
        requested_shift_id=requested_shift_id,
        reason=reason
    )
    
    logger.info(f"Shift swap request created: {swap_request.id}")
    return swap_request


def get_staff_schedule(cluster, staff_member, start_date, end_date):
    """Get schedule for a staff member."""
    return Shift.objects.filter(
        cluster=cluster,
        assigned_staff=staff_member,
        start_time__gte=start_date,
        end_time__lte=end_date
    ).order_by('start_time')


# Notification helper functions
def send_missed_shift_notification(shift):
    """Send missed shift notification."""
    try:
        notifications.send(
            event_name=NotificationEvents.SHIFT_MISSED,
            recipients=[shift.assigned_staff],
            cluster=shift.cluster,
            context={
                'shift_title': shift.title,
                'shift_date': shift.start_time.strftime('%Y-%m-%d'),
                'shift_time': f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}",
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send missed shift notification: {e}")
        return False


def send_swap_response_notification(swap_request):
    """Send shift swap response notification."""
    try:
        notifications.send(
            event_name=NotificationEvents.SHIFT_SWAP_RESPONSE,
            recipients=[swap_request.requested_by],
            cluster=swap_request.original_shift.cluster,
            context={
                'swap_status': swap_request.status,
                'original_shift': swap_request.original_shift.title,
                'response_date': timezone.now().strftime('%Y-%m-%d'),
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send swap response notification: {e}")
        return False

def mark_missed_shifts():
    """Mark shifts as no-show if they were missed."""
    from django.utils import timezone
    
    now = timezone.now()
    missed_shifts = Shift.objects.filter(
        start_time__lt=now,
        status=ShiftStatus.SCHEDULED,
        actual_start_time__isnull=True
    )
    
    count = 0
    for shift in missed_shifts:
        shift.status = ShiftStatus.NO_SHOW
        shift.save()
        
        # Send missed shift notification
        send_missed_shift_notification(shift)
        count += 1
    
    logger.info(f"Marked {count} shifts as no-show")
    return count


def send_upcoming_reminders():
    """Send reminders for upcoming shifts."""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    reminder_time = now + timedelta(hours=2)  # 2 hours before shift
    
    upcoming_shifts = Shift.objects.filter(
        start_time__gte=now,
        start_time__lte=reminder_time,
        status=ShiftStatus.SCHEDULED
    )
    
    count = 0
    for shift in upcoming_shifts:
        try:
            notifications.send(
                event_name=NotificationEvents.SHIFT_REMINDER,
                recipients=[shift.assigned_staff],
                cluster=shift.cluster,
                context={
                    'shift_title': shift.title,
                    'shift_date': shift.start_time.strftime('%Y-%m-%d'),
                    'shift_time': f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}",
                    'location': shift.location or 'Not specified',
                }
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to send shift reminder for {shift.id}: {e}")
    
    logger.info(f"Sent {count} shift reminders")
    return count

def send_assignment_notification(shift):
    """Send shift assignment notification."""
    try:
        notifications.send(
            event_name=NotificationEvents.SHIFT_ASSIGNED,
            recipients=[shift.assigned_staff],
            cluster=shift.cluster,
            context={
                'shift_title': shift.title,
                'shift_date': shift.start_time.strftime('%Y-%m-%d'),
                'shift_time': f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}",
                'location': shift.location or 'Not specified',
                'shift_type': shift.get_shift_type_display(),
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send shift assignment notification: {e}")
        return False


def send_reminder_notification(shift):
    """Send shift reminder notification."""
    try:
        notifications.send(
            event_name=NotificationEvents.SHIFT_REMINDER,
            recipients=[shift.assigned_staff],
            cluster=shift.cluster,
            context={
                'shift_title': shift.title,
                'shift_date': shift.start_time.strftime('%Y-%m-%d'),
                'shift_time': f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}",
                'location': shift.location or 'Not specified',
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send shift reminder notification: {e}")
        return False


def send_swap_request_notification(swap_request):
    """Send shift swap request notification."""
    try:
        notifications.send(
            event_name=NotificationEvents.SHIFT_SWAP_REQUEST,
            recipients=[swap_request.requested_with],
            cluster=swap_request.cluster,
            context={
                'requester_name': swap_request.requested_by.name,
                'original_shift': swap_request.original_shift.title,
                'original_date': swap_request.original_shift.start_time.strftime('%Y-%m-%d'),
                'target_shift': swap_request.target_shift.title if swap_request.target_shift else 'Open request',
                'reason': swap_request.reason,
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send swap request notification: {e}")
        return False


def get_statistics(cluster, start_date=None, end_date=None):
    """Get shift statistics for a cluster."""
    shifts_qs = Shift.objects.filter(cluster=cluster)
    
    if start_date:
        shifts_qs = shifts_qs.filter(start_time__gte=start_date)
    if end_date:
        shifts_qs = shifts_qs.filter(end_time__lte=end_date)
    
    total_shifts = shifts_qs.count()
    completed_shifts = shifts_qs.filter(status=ShiftStatus.COMPLETED).count()
    no_show_shifts = shifts_qs.filter(status=ShiftStatus.NO_SHOW).count()
    cancelled_shifts = shifts_qs.filter(status=ShiftStatus.CANCELLED).count()
    
    # Calculate attendance rate (completed / (total - cancelled))
    eligible_shifts = total_shifts - cancelled_shifts
    attendance_rate = (completed_shifts / eligible_shifts * 100) if eligible_shifts > 0 else 0
    
    # Calculate average overtime hours
    completed_with_attendance = shifts_qs.filter(
        status=ShiftStatus.COMPLETED,
        attendance__isnull=False
    ).select_related('attendance')
    
    total_overtime_seconds = 0
    overtime_count = 0
    for shift in completed_with_attendance:
        if shift.attendance and shift.attendance.overtime_hours:
            total_overtime_seconds += shift.attendance.overtime_hours.total_seconds()
            overtime_count += 1
    
    average_overtime_hours = (total_overtime_seconds / 3600 / overtime_count) if overtime_count > 0 else 0
    
    return {
        'total_shifts': total_shifts,
        'completed_shifts': completed_shifts,
        'no_show_shifts': no_show_shifts,
        'cancelled_shifts': cancelled_shifts,
        'missed_shifts': no_show_shifts,  # Alias for compatibility
        'in_progress_shifts': shifts_qs.filter(status=ShiftStatus.IN_PROGRESS).count(),
        'attendance_rate': round(attendance_rate, 2),
        'average_overtime_hours': round(average_overtime_hours, 2),
    }