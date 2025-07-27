"""
Shift management utilities for ClustR application.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.exceptions import ValidationError

from core.common.models import Shift, ShiftAttendance, ShiftSwapRequest, ShiftStatus
from core.common.utils.notification_utils import NotificationManager

logger = logging.getLogger('clustr')


class ShiftManager:
    """
    Manages shift-related operations and business logic.
    """
    
    @staticmethod
    def create_shift(cluster, title, shift_type, assigned_staff, start_time, end_time, **kwargs):
        """
        Create a new shift with conflict detection.
        
        Args:
            cluster: The cluster this shift belongs to
            title: Title of the shift
            shift_type: Type of shift (from ShiftType choices)
            assigned_staff: Staff member assigned to the shift
            start_time: Scheduled start time
            end_time: Scheduled end time
            **kwargs: Additional shift parameters
        
        Returns:
            Shift: The created shift object
        
        Raises:
            ValidationError: If there are scheduling conflicts
        """
        # Check for overlapping shifts
        conflicts = ShiftManager.check_shift_conflicts(
            cluster, assigned_staff, start_time, end_time
        )
        
        if conflicts:
            conflict_details = [
                f"{shift.title} ({shift.start_time.strftime('%Y-%m-%d %H:%M')} - {shift.end_time.strftime('%H:%M')})"
                for shift in conflicts
            ]
            raise ValidationError(
                f"Shift conflicts detected with: {', '.join(conflict_details)}"
            )
        
        shift = Shift.objects.create(
            cluster=cluster,
            title=title,
            shift_type=shift_type,
            assigned_staff=assigned_staff,
            start_time=start_time,
            end_time=end_time,
            **kwargs
        )
        
        # Create attendance record
        ShiftAttendance.objects.create(
            cluster=cluster,
            shift=shift
        )
        
        # Send notification to assigned staff
        ShiftNotificationManager.send_shift_assignment_notification(shift)
        
        return shift
    
    @staticmethod
    def check_shift_conflicts(cluster, staff_member, start_time, end_time, exclude_shift_id=None):
        """
        Check for overlapping shifts for a staff member.
        
        Args:
            cluster: The cluster to check within
            staff_member: Staff member to check conflicts for
            start_time: Start time of the new shift
            end_time: End time of the new shift
            exclude_shift_id: Shift ID to exclude from conflict check (for updates)
        
        Returns:
            QuerySet: Conflicting shifts
        """
        conflicts = Shift.objects.filter(
            cluster=cluster,
            assigned_staff=staff_member,
            status__in=[ShiftStatus.SCHEDULED, ShiftStatus.IN_PROGRESS]
        )
        
        if exclude_shift_id:
            conflicts = conflicts.exclude(id=exclude_shift_id)
        
        # Check for time overlap
        conflicts = conflicts.filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        
        return conflicts
    
    @staticmethod
    def clock_in_staff(shift, clock_in_time=None):
        """
        Clock in a staff member for their shift.
        
        Args:
            shift_id: ID of the shift to clock in for
            clock_in_time: Time of clock in (defaults to now)
        
        Returns:
            Shift: Updated shift object
        
        Raises:
            ValidationError: If clock in is not allowed
        """
        try:
            if shift.status != ShiftStatus.SCHEDULED:
                raise ValidationError("Can only clock in for scheduled shifts")
            
            clock_in_time = clock_in_time or timezone.now()
            
            # Update shift
            shift.clock_in(clock_in_time)
            
            # Update attendance record
            attendance = shift.attendance
            attendance.clock_in_time = clock_in_time
            attendance.calculate_late_arrival()
            attendance.save()
            
            logger.info(f"Staff {shift.assigned_staff.name} clocked in for shift {shift.title}")
            
            return shift
            
        except Shift.DoesNotExist:
            raise ValidationError("Shift not found")
    
    @staticmethod
    def clock_out_staff(shift, clock_out_time=None):
        """
        Clock out a staff member from their shift.
        
        Args:
            shift_id: ID of the shift to clock out from
            clock_out_time: Time of clock out (defaults to now)
        
        Returns:
            Shift: Updated shift object
        
        Raises:
            ValidationError: If clock out is not allowed
        """
        try:
            if shift.status != ShiftStatus.IN_PROGRESS:
                raise ValidationError("Can only clock out from shifts in progress")
            
            clock_out_time = clock_out_time or timezone.now()
            
            # Update shift
            shift.clock_out(clock_out_time)
            
            # Update attendance record
            attendance = shift.attendance
            attendance.clock_out_time = clock_out_time
            attendance.calculate_overtime()
            attendance.calculate_early_departure()
            attendance.save()
            
            logger.info(f"Staff {shift.assigned_staff.name} clocked out from shift {shift.title}")
            
            return shift
            
        except Shift.DoesNotExist:
            raise ValidationError("Shift not found")
    
    @staticmethod
    def create_shift_swap_request(original_shift_id, requested_by, requested_with, target_shift_id=None, reason=""):
        """
        Create a shift swap request.
        
        Args:
            original_shift_id: ID of the shift to be swapped
            requested_by: User requesting the swap
            requested_with: User to swap with
            target_shift_id: ID of the target shift (optional for coverage requests)
            reason: Reason for the swap
        
        Returns:
            ShiftSwapRequest: The created swap request
        
        Raises:
            ValidationError: If swap request is invalid
        """
        try:
            original_shift = Shift.objects.get(id=original_shift_id)
            
            if original_shift.assigned_staff != requested_by:
                raise ValidationError("You can only request swaps for your own shifts")
            
            if original_shift.status != ShiftStatus.SCHEDULED:
                raise ValidationError("Can only swap scheduled shifts")
            
            target_shift = None
            if target_shift_id:
                target_shift = Shift.objects.get(id=target_shift_id)
                
                if target_shift.assigned_staff != requested_with:
                    raise ValidationError("Target shift must be assigned to the person you're swapping with")
                
                if target_shift.status != ShiftStatus.SCHEDULED:
                    raise ValidationError("Can only swap with scheduled shifts")
            
            swap_request = ShiftSwapRequest.objects.create(
                cluster=original_shift.cluster,
                original_shift=original_shift,
                requested_by=requested_by,
                requested_with=requested_with,
                target_shift=target_shift,
                reason=reason
            )
            
            # Send notification to the other staff member
            ShiftNotificationManager.send_swap_request_notification(swap_request)
            
            return swap_request
            
        except Shift.DoesNotExist:
            raise ValidationError("Shift not found")
    
    @staticmethod
    def get_staff_schedule(cluster, staff_member, start_date=None, end_date=None):
        """
        Get schedule for a staff member within a date range.
        
        Args:
            cluster: The cluster to get schedule for
            staff_member: Staff member to get schedule for
            start_date: Start date for schedule (defaults to today)
            end_date: End date for schedule (defaults to 7 days from start)
        
        Returns:
            QuerySet: Shifts for the staff member
        """
        if not start_date:
            start_date = timezone.now().date()
        
        if not end_date:
            end_date = start_date + timedelta(days=7)
        
        return Shift.objects.filter(
            cluster=cluster,
            assigned_staff=staff_member,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).order_by('start_time')
    
    @staticmethod
    def get_shift_statistics(cluster, start_date=None, end_date=None):
        """
        Get shift statistics for a cluster.
        
        Args:
            cluster: The cluster to get statistics for
            start_date: Start date for statistics
            end_date: End date for statistics
        
        Returns:
            dict: Statistics about shifts
        """
        shifts = Shift.objects.filter(cluster=cluster)
        
        if start_date:
            shifts = shifts.filter(start_time__date__gte=start_date)
        
        if end_date:
            shifts = shifts.filter(start_time__date__lte=end_date)
        
        total_shifts = shifts.count()
        completed_shifts = shifts.filter(status=ShiftStatus.COMPLETED).count()
        no_show_shifts = shifts.filter(status=ShiftStatus.NO_SHOW).count()
        cancelled_shifts = shifts.filter(status=ShiftStatus.CANCELLED).count()
        
        # Calculate attendance rate
        attendance_rate = (completed_shifts / total_shifts * 100) if total_shifts > 0 else 0
        
        # Get average overtime
        attendances = ShiftAttendance.objects.filter(
            shift__cluster=cluster,
            shift__in=shifts,
            overtime_hours__gt=timedelta(0)
        )
        
        avg_overtime = attendances.aggregate(
            avg_overtime=Avg('overtime_hours')
        )['avg_overtime'] or timedelta(0)
        
        return {
            'total_shifts': total_shifts,
            'completed_shifts': completed_shifts,
            'no_show_shifts': no_show_shifts,
            'cancelled_shifts': cancelled_shifts,
            'attendance_rate': round(attendance_rate, 2),
            'average_overtime_hours': avg_overtime.total_seconds() / 3600 if avg_overtime else 0,
        }
    
    @staticmethod
    def mark_missed_shifts():
        """
        Mark shifts as no-show if they're past their end time and not completed.
        This should be run as a scheduled task.
        """
        now = timezone.now()
        missed_shifts = Shift.objects.filter(
            status=ShiftStatus.SCHEDULED,
            end_time__lt=now - timedelta(minutes=30)  # Grace period of 30 minutes
        )
        
        for shift in missed_shifts:
            shift.mark_no_show()
            ShiftNotificationManager.send_missed_shift_notification(shift)
            logger.warning(f"Marked shift as no-show: {shift.title} for {shift.assigned_staff.name}")
    
    @staticmethod
    def send_upcoming_shift_reminders():
        """
        Send reminders for upcoming shifts.
        This should be run as a scheduled task.
        """
        now = timezone.now()
        upcoming_shifts = Shift.objects.filter(
            status=ShiftStatus.SCHEDULED,
            start_time__gte=now,
            start_time__lte=now + timedelta(hours=2)  # 2 hours before shift
        )
        
        for shift in upcoming_shifts:
            ShiftNotificationManager.send_shift_reminder_notification(shift)


class ShiftNotificationManager:
    """
    Manages notifications related to shift management.
    """
    
    @staticmethod
    def send_shift_assignment_notification(shift):
        """
        Send notification when a shift is assigned to a staff member.
        
        Args:
            shift: The shift object
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            if shift.assigned_staff.email_address:
                # This would use the existing notification system
                # For now, we'll log the notification
                logger.info(
                    f"Shift assignment notification sent to {shift.assigned_staff.email_address} "
                    f"for shift: {shift.title} on {shift.start_time.strftime('%Y-%m-%d %H:%M')}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send shift assignment notification: {e}")
            return False
    
    @staticmethod
    def send_shift_reminder_notification(shift):
        """
        Send reminder notification for upcoming shift.
        
        Args:
            shift: The shift object
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            if shift.assigned_staff.email_address:
                logger.info(
                    f"Shift reminder notification sent to {shift.assigned_staff.email_address} "
                    f"for shift: {shift.title} starting at {shift.start_time.strftime('%Y-%m-%d %H:%M')}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send shift reminder notification: {e}")
            return False
    
    @staticmethod
    def send_missed_shift_notification(shift):
        """
        Send notification when a staff member misses a shift.
        
        Args:
            shift: The shift object
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Notify the staff member and administrators
            recipients = [shift.assigned_staff.email_address]
            
            # Add cluster admins
            from accounts.models import AccountUser
            admins = AccountUser.objects.filter(
                clusters=shift.cluster,
                is_cluster_admin=True
            )
            recipients.extend([admin.email_address for admin in admins if admin.email_address])
            
            for recipient in recipients:
                logger.info(
                    f"Missed shift notification sent to {recipient} "
                    f"for shift: {shift.title} on {shift.start_time.strftime('%Y-%m-%d %H:%M')}"
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send missed shift notification: {e}")
            return False
    
    @staticmethod
    def send_swap_request_notification(swap_request):
        """
        Send notification for shift swap request.
        
        Args:
            swap_request: The swap request object
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            if swap_request.requested_with.email_address:
                logger.info(
                    f"Shift swap request notification sent to {swap_request.requested_with.email_address} "
                    f"from {swap_request.requested_by.name} for shift: {swap_request.original_shift.title}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send swap request notification: {e}")
            return False
    
    @staticmethod
    def send_swap_response_notification(swap_request):
        """
        Send notification when swap request is approved/rejected.
        
        Args:
            swap_request: The swap request object
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            if swap_request.requested_by.email_address:
                status = "approved" if swap_request.status == ShiftSwapRequest.SwapStatus.APPROVED else "rejected"
                logger.info(
                    f"Shift swap {status} notification sent to {swap_request.requested_by.email_address} "
                    f"for shift: {swap_request.original_shift.title}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send swap response notification: {e}")
            return False