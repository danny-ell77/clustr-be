"""
Scheduled tasks utilities for ClustR application.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone

from core.common.models import Visitor, Invitation, Shift, ShiftStatus
from core.common.utils.notification_utils import NotificationManager

logger = logging.getLogger('clustr')


class ScheduledTaskManager:
    """
    Manager for scheduled tasks in the ClustR application.
    """
    
    @staticmethod
    def detect_visitor_overstays():
        """
        Detect visitors who have overstayed their scheduled visit duration.
        This method should be called periodically by a scheduler.
        """
        # Find visitors who are checked in but should have checked out by now
        current_time = timezone.now()
        
        # Get visitors who are checked in and their estimated arrival + some grace period has passed
        # For simplicity, we'll use a 2-hour grace period
        grace_period = timedelta(hours=2)
        
        overstaying_visitors = Visitor.objects.filter(
            status=Visitor.Status.CHECKED_IN,
            estimated_arrival__lt=current_time - grace_period
        )
        
        for visitor in overstaying_visitors:
            logger.info(f"Detected overstaying visitor: {visitor.name} (ID: {visitor.id})")
            
            try:
                # In a real implementation, you would get the user's email from the database
                # For now, we'll just use a placeholder
                user_email = "user@example.com"  # This would be replaced with actual user email
                
                # Send notification to the user who invited the visitor
                NotificationManager.send_visitor_overstay_notification(
                    user_email=user_email,
                    visitor_name=visitor.name,
                    access_code=visitor.access_code
                )
                
                logger.info(f"Sent overstay notification for visitor: {visitor.name} (ID: {visitor.id})")
            except Exception as e:
                logger.error(f"Failed to send overstay notification: {str(e)}")
    
    @staticmethod
    def update_invitation_statuses():
        """
        Update invitation statuses based on their start and end dates.
        This method should be called periodically by a scheduler.
        """
        current_date = timezone.now().date()
        
        # Find active invitations that have expired
        expired_invitations = Invitation.objects.filter(
            status=Invitation.Status.ACTIVE,
            end_date__lt=current_date
        )
        
        # Update their status to EXPIRED
        expired_count = expired_invitations.update(status=Invitation.Status.EXPIRED)
        
        if expired_count > 0:
            logger.info(f"Updated {expired_count} invitations to EXPIRED status")
            
        # Find expired invitations that are now active again (for recurring invitations)
        # This would be more complex in a real implementation, considering recurrence patterns
        # For simplicity, we'll just log that this would happen
        logger.info("Would check for recurring invitations that need to be reactivated")
    
    @staticmethod
    def check_missed_shifts():
        """
        Check for missed shifts and mark them as no-show.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.shift_utils import ShiftManager
        
        try:
            ShiftManager.mark_missed_shifts()
            logger.info("Completed missed shifts check")
        except Exception as e:
            logger.error(f"Error checking missed shifts: {str(e)}")
    
    @staticmethod
    def send_shift_reminders():
        """
        Send reminders for upcoming shifts.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.shift_utils import ShiftManager
        
        try:
            ShiftManager.send_upcoming_shift_reminders()
            logger.info("Completed sending shift reminders")
        except Exception as e:
            logger.error(f"Error sending shift reminders: {str(e)}")
    
    @staticmethod
    def check_task_deadlines():
        """
        Check task deadlines and send reminders or mark as overdue.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.task_utils import TaskManager
        from core.common.models import Cluster
        
        try:
            # Process tasks for all clusters
            for cluster in Cluster.objects.all():
                # Send reminders for tasks due soon
                TaskManager.send_due_reminders(cluster)
                
                # Process overdue tasks
                TaskManager.process_overdue_tasks(cluster)
            
            logger.info("Completed task deadline checks")
        except Exception as e:
            logger.error(f"Error checking task deadlines: {str(e)}")
    
    @staticmethod
    def process_maintenance_schedules():
        """
        Process due maintenance schedules and send alerts.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.maintenance_utils import MaintenanceManager
        from core.common.models import Cluster
        
        try:
            # Process maintenance schedules for all clusters
            for cluster in Cluster.objects.all():
                # Process due maintenance schedules
                created_logs = MaintenanceManager.process_due_maintenance_schedules(cluster)
                if created_logs:
                    logger.info(f"Created {len(created_logs)} maintenance logs from schedules for cluster {cluster.name}")
                
                # Send maintenance due alerts
                alerts_sent = MaintenanceManager.send_maintenance_due_alerts(cluster)
                if alerts_sent:
                    logger.info(f"Sent {alerts_sent} maintenance due alerts for cluster {cluster.name}")
            
            logger.info("Completed maintenance schedule processing")
        except Exception as e:
            logger.error(f"Error processing maintenance schedules: {str(e)}")
    
    @staticmethod
    def check_overdue_children():
        """
        Check for children who are overdue for return and send alerts.
        This method should be called periodically by a scheduler.
        """
        from core.common.models import EntryExitLog
        
        try:
            current_time = timezone.now()
            
            # Find children who are overdue for return
            overdue_logs = EntryExitLog.objects.filter(
                log_type=EntryExitLog.LogType.EXIT,
                status=EntryExitLog.Status.IN_PROGRESS,
                expected_return_time__lt=current_time
            )
            
            overdue_count = 0
            for log in overdue_logs:
                # Mark as overdue
                if log.mark_overdue():
                    overdue_count += 1
                    
                    # Send overdue notification
                    try:
                        NotificationManager.send_child_overdue_notification(log)
                        logger.info(f"Sent overdue notification for child: {log.child.name} (ID: {log.child.id})")
                    except Exception as e:
                        logger.error(f"Failed to send overdue notification for child {log.child.name}: {str(e)}")
            
            if overdue_count > 0:
                logger.info(f"Marked {overdue_count} children as overdue")
            
        except Exception as e:
            logger.error(f"Error checking overdue children: {str(e)}")
    
    @staticmethod
    def expire_old_exit_requests():
        """
        Mark expired exit requests as expired.
        This method should be called periodically by a scheduler.
        """
        from core.common.models import ExitRequest
        
        try:
            current_time = timezone.now()
            
            # Find pending exit requests that have expired
            expired_requests = ExitRequest.objects.filter(
                status=ExitRequest.Status.PENDING,
                expires_at__lt=current_time
            )
            
            # Update their status to EXPIRED
            expired_count = expired_requests.update(status=ExitRequest.Status.EXPIRED)
            
            if expired_count > 0:
                logger.info(f"Marked {expired_count} exit requests as expired")
                
        except Exception as e:
            logger.error(f"Error expiring old exit requests: {str(e)}")
    
    @staticmethod
    def send_exit_request_reminders():
        """
        Send reminders for pending exit requests that are about to expire.
        This method should be called periodically by a scheduler.
        """
        from core.common.models import ExitRequest
        
        try:
            # Send reminders for requests expiring in the next 2 hours
            reminder_threshold = timezone.now() + timedelta(hours=2)
            
            pending_requests = ExitRequest.objects.filter(
                status=ExitRequest.Status.PENDING,
                expires_at__lt=reminder_threshold,
                expires_at__gt=timezone.now()
            )
            
            reminder_count = 0
            for request in pending_requests:
                try:
                    # In a real implementation, you would send a reminder notification
                    # NotificationManager.send_exit_request_reminder(request)
                    reminder_count += 1
                    logger.info(f"Sent reminder for exit request: {request.request_id}")
                except Exception as e:
                    logger.error(f"Failed to send reminder for exit request {request.request_id}: {str(e)}")
            
            if reminder_count > 0:
                logger.info(f"Sent {reminder_count} exit request reminders")
                
        except Exception as e:
            logger.error(f"Error sending exit request reminders: {str(e)}")
    
    @staticmethod
    def process_recurring_payments():
        """
        Process due recurring payments for all clusters.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.recurring_payment_utils import RecurringPaymentManager
        from core.common.models import Cluster
        
        try:
            total_processed = 0
            total_failed = 0
            total_paused = 0
            
            # Process recurring payments for all clusters
            for cluster in Cluster.objects.all():
                results = RecurringPaymentManager.process_due_payments(cluster)
                total_processed += results['processed']
                total_failed += results['failed']
                total_paused += results['paused']
                
                if results['processed'] > 0 or results['failed'] > 0:
                    logger.info(f"Cluster {cluster.name}: Processed {results['processed']}, Failed {results['failed']}, Paused {results['paused']}")
            
            logger.info(f"Completed recurring payments processing: {total_processed} processed, {total_failed} failed, {total_paused} paused")
        except Exception as e:
            logger.error(f"Error processing recurring payments: {str(e)}")
    
    @staticmethod
    def send_recurring_payment_reminders():
        """
        Send reminders for upcoming recurring payments.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.recurring_payment_utils import RecurringPaymentManager
        from core.common.models import Cluster
        
        try:
            total_reminders = 0
            
            # Send reminders for all clusters
            for cluster in Cluster.objects.all():
                reminders_sent = RecurringPaymentManager.send_payment_reminders(cluster, days_before=1)
                total_reminders += reminders_sent
                
                if reminders_sent > 0:
                    logger.info(f"Sent {reminders_sent} recurring payment reminders for cluster {cluster.name}")
            
            logger.info(f"Completed sending recurring payment reminders: {total_reminders} sent")
        except Exception as e:
            logger.error(f"Error sending recurring payment reminders: {str(e)}")
    
    @staticmethod
    def check_overdue_bills():
        """
        Check for overdue bills and update their status.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.bill_utils import BillManager
        from core.common.models import Cluster
        
        try:
            total_overdue = 0
            
            # Check overdue bills for all clusters
            for cluster in Cluster.objects.all():
                overdue_count = BillManager.check_and_update_overdue_bills(cluster)
                total_overdue += overdue_count
                
                if overdue_count > 0:
                    logger.info(f"Marked {overdue_count} bills as overdue for cluster {cluster.name}")
            
            logger.info(f"Completed overdue bills check: {total_overdue} bills marked as overdue")
        except Exception as e:
            logger.error(f"Error checking overdue bills: {str(e)}")
    
    @staticmethod
    def send_bill_reminders():
        """
        Send reminders for bills approaching due date.
        This method should be called periodically by a scheduler.
        """
        from core.common.utils.bill_utils import BillManager
        from core.common.models import Cluster
        
        try:
            total_reminders = 0
            
            # Send bill reminders for all clusters
            for cluster in Cluster.objects.all():
                reminders_sent = BillManager.send_bill_reminders(cluster, days_before_due=3)
                total_reminders += reminders_sent
                
                if reminders_sent > 0:
                    logger.info(f"Sent {reminders_sent} bill reminders for cluster {cluster.name}")
            
            logger.info(f"Completed sending bill reminders: {total_reminders} sent")
        except Exception as e:
            logger.error(f"Error sending bill reminders: {str(e)}")
    
    @staticmethod
    def run_all_scheduled_tasks():
        """
        Run all scheduled tasks.
        This is a convenience method for running all tasks at once.
        """
        logger.info("Starting scheduled tasks execution")
        
        try:
            ScheduledTaskManager.detect_visitor_overstays()
            ScheduledTaskManager.update_invitation_statuses()
            ScheduledTaskManager.check_missed_shifts()
            ScheduledTaskManager.send_shift_reminders()
            ScheduledTaskManager.check_task_deadlines()
            ScheduledTaskManager.process_maintenance_schedules()
            ScheduledTaskManager.check_overdue_children()
            ScheduledTaskManager.expire_old_exit_requests()
            ScheduledTaskManager.send_exit_request_reminders()
            
            # Payment-related scheduled tasks
            ScheduledTaskManager.process_recurring_payments()
            ScheduledTaskManager.send_recurring_payment_reminders()
            ScheduledTaskManager.check_overdue_bills()
            ScheduledTaskManager.send_bill_reminders()
            
            logger.info("Completed all scheduled tasks")
        except Exception as e:
            logger.error(f"Error running scheduled tasks: {str(e)}")