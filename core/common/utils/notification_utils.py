"""
Notification utilities for ClustR application.
"""

import logging
from typing import List, Optional
from django.template import Context
from django.utils.translation import gettext_lazy as _

from core.common.email_sender import AccountEmailSender, NotificationTypes

logger = logging.getLogger('clustr')


class NotificationManager:
    """
    Manages sending notifications to users with preference-based filtering.
    """
    
    @staticmethod
    def _filter_recipients_by_preferences(
        recipients: List[str], 
        notification_type: str, 
        channel: str = "EMAIL",
        cluster=None
    ) -> List[str]:
        """
        Filter recipients based on their notification preferences.
        
        Args:
            recipients: List of email addresses
            notification_type: Type of notification
            channel: Notification channel (EMAIL, SMS, PUSH, IN_APP)
            cluster: Optional cluster for cluster-specific preferences
            
        Returns:
            Filtered list of recipients who have this notification enabled
        """
        try:
            from accounts.models import AccountUser, UserSettings
            
            # Get users by email addresses
            users = AccountUser.objects.filter(email_address__in=recipients)
            filtered_recipients = []
            
            for user in users:
                # Get or create user settings
                settings, created = UserSettings.objects.get_or_create(user=user)
                
                # Check if user has this notification enabled for this channel
                if settings.get_notification_preference(notification_type, channel):
                    filtered_recipients.append(user.email_address)
            
            return filtered_recipients
            
        except Exception as e:
            logger.error(f"Error filtering recipients by preferences: {e}")
            # Return original recipients if filtering fails
            return recipients
    
    @staticmethod
    def _send_notification_with_preferences(
        recipients: List[str],
        notification_type: str,
        email_type: str,
        context: Context,
        channel: str = "EMAIL",
        cluster=None
    ) -> bool:
        """
        Send notification with preference filtering.
        
        Args:
            recipients: List of email addresses
            notification_type: Type of notification for preference checking
            email_type: Email template type
            context: Email context
            channel: Notification channel
            cluster: Optional cluster
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            # Filter recipients based on preferences
            filtered_recipients = NotificationManager._filter_recipients_by_preferences(
                recipients, notification_type, channel, cluster
            )
            
            if not filtered_recipients:
                logger.info(f"No recipients with {notification_type} notifications enabled")
                return True
            
            sender = AccountEmailSender(
                recipients=filtered_recipients,
                email_type=email_type,
                context=context
            )
            
            return sender.send()
            
        except Exception as e:
            logger.error(f"Error sending notification with preferences: {e}")
            return False
    
    @staticmethod
    def _send_sms_notification_with_preferences(
        phone_numbers: List[str],
        notification_type: str,
        message: str,
        cluster=None
    ) -> bool:
        """
        Send SMS notification with preference filtering.
        
        Args:
            phone_numbers: List of phone numbers
            notification_type: Type of notification for preference checking
            message: SMS message content
            cluster: Optional cluster
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            from accounts.models import AccountUser, UserSettings, SMSSender
            
            # Get users by phone numbers
            users = AccountUser.objects.filter(phone_number__in=phone_numbers)
            filtered_phone_numbers = []
            
            for user in users:
                # Get or create user settings
                settings, created = UserSettings.objects.get_or_create(user=user)
                
                # Check if user has SMS notifications enabled for this type
                if settings.get_notification_preference(notification_type, "SMS"):
                    filtered_phone_numbers.append(user.phone_number)
            
            if not filtered_phone_numbers:
                logger.info(f"No recipients with SMS {notification_type} notifications enabled")
                return True
            
            # Send SMS to filtered recipients
            success_count = 0
            for phone_number in filtered_phone_numbers:
                if SMSSender.send_verification_code(phone_number, message):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending SMS notification with preferences: {e}")
            return False
    
    @staticmethod
    def send_multi_channel_notification(
        recipients: List[str],
        notification_type: str,
        email_type: str,
        email_context: Context,
        sms_message: str = None,
        cluster=None
    ) -> dict:
        """
        Send notification across multiple channels based on user preferences.
        
        Args:
            recipients: List of email addresses or phone numbers
            notification_type: Type of notification
            email_type: Email template type
            email_context: Email context
            sms_message: SMS message content (optional)
            cluster: Optional cluster
            
        Returns:
            Dictionary with results for each channel
        """
        results = {
            'email': False,
            'sms': False,
        }
        
        try:
            # Send email notifications
            results['email'] = NotificationManager._send_notification_with_preferences(
                recipients=recipients,
                notification_type=notification_type,
                email_type=email_type,
                context=email_context,
                channel="EMAIL",
                cluster=cluster
            )
            
            # Send SMS notifications if message provided
            if sms_message:
                # Convert email addresses to phone numbers
                from accounts.models import AccountUser
                users = AccountUser.objects.filter(email_address__in=recipients)
                phone_numbers = [user.phone_number for user in users if user.phone_number]
                
                if phone_numbers:
                    results['sms'] = NotificationManager._send_sms_notification_with_preferences(
                        phone_numbers=phone_numbers,
                        notification_type=notification_type,
                        message=sms_message,
                        cluster=cluster
                    )
            
            return results
            
        except Exception as e:
            logger.error(f"Error sending multi-channel notification: {e}")
            return results
    
    @staticmethod
    def send_visitor_arrival_notification(user_email, visitor_name, access_code):
        """
        Send a notification when a visitor arrives.
        
        Args:
            user_email: Email of the user to notify
            visitor_name: Name of the visitor
            access_code: Access code of the visitor
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        context = Context({
            'visitor_name': visitor_name,
            'access_code': access_code,
        })
        
        return NotificationManager._send_notification_with_preferences(
            recipients=[user_email],
            notification_type="VISITOR_ARRIVAL",
            email_type=NotificationTypes.VISITOR_ARRIVAL,
            context=context
        )
    
    @staticmethod
    def send_visitor_overstay_notification(user_email, visitor_name, access_code):
        """
        Send a notification when a visitor overstays.
        
        Args:
            user_email: Email of the user to notify
            visitor_name: Name of the visitor
            access_code: Access code of the visitor
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        context = Context({
            'visitor_name': visitor_name,
            'access_code': access_code,
        })
        
        return NotificationManager._send_notification_with_preferences(
            recipients=[user_email],
            notification_type="VISITOR_OVERSTAY",
            email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder
            context=context
        )
    
    @staticmethod
    def send_announcement_notification(announcement, cluster):
        """
        Send a notification when a new announcement is published.
        
        Args:
            announcement: The announcement object
            cluster: The cluster object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            # Get all users in the cluster
            from accounts.models import AccountUser
            cluster_users = AccountUser.objects.filter(clusters_in=[cluster])
            
            context = Context({
                'announcement_title': announcement.title,
                'announcement_content': announcement.content[:200] + '...' if len(announcement.content) > 200 else announcement.content,
                'cluster_name': cluster.name,
                'category': announcement.get_category_display(),
            })
            
            # Send to all cluster users
            user_emails = [user.email_address for user in cluster_users if user.email_address]
            
            if user_emails:
                sender = AccountEmailSender(
                    recipients=user_emails,
                    email_type="__placeholder__",  # Placeholder - would need ANNOUNCEMENT type
                    context=context
                )
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send announcement notification: {e}")
            return False
    
    @staticmethod
    def send_comment_notification(comment, announcement):
        """
        Send a notification when someone comments on an announcement.
        
        Args:
            comment: The comment object
            announcement: The announcement object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            # Get the announcement author
            from accounts.models import AccountUser
            author = AccountUser.objects.filter(id=announcement.author_id).first()
            
            if not author or not author.email_address:
                return False
            
            context = Context({
                'announcement_title': announcement.title,
                'comment_content': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                'commenter_name': 'A user',  # Would need to get actual commenter name
            })
            
            sender = AccountEmailSender(
                recipients=[author.email_address],
                email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need COMMENT type
                context=context
            )
            
            return sender.send()
        except Exception as e:
            logger.error(f"Failed to send comment notification: {e}")
            return False
    
    @staticmethod
    def send_issue_status_notification(issue, old_status, new_status, changed_by):
        """
        Send a notification when an issue status changes.
        
        Args:
            issue: The issue ticket object
            old_status: The previous status
            new_status: The new status
            changed_by: The user who changed the status
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            # Notify the issue reporter
            if issue.reported_by and issue.reported_by.email_address:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by_name': changed_by.name,
                })
                
                sender = AccountEmailSender(
                    recipients=[issue.reported_by.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_STATUS_CHANGE type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue status notification: {e}")
            return False
    
    @staticmethod
    def send_issue_comment_notification(comment, issue):
        """
        Send a notification when someone comments on an issue.
        
        Args:
            comment: The comment object
            issue: The issue ticket object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            recipients = []
            
            # Notify the issue reporter if they're not the commenter
            if issue.reported_by and issue.reported_by != comment.author and issue.reported_by.email_address:
                recipients.append(issue.reported_by.email_address)
            
            # Notify the assigned staff if they're not the commenter
            if issue.assigned_to and issue.assigned_to != comment.author and issue.assigned_to.email_address:
                recipients.append(issue.assigned_to.email_address)
            
            if recipients:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'comment_content': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                    'commenter_name': comment.author.name,
                })
                
                sender = AccountEmailSender(
                    recipients=recipients,
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_COMMENT type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue comment notification: {e}")
            return False
    
    @staticmethod
    def send_issue_assignment_notification(issue, assigned_to):
        """
        Send a notification when an issue is assigned to a staff member.
        
        Args:
            issue: The issue ticket object
            assigned_to: The user the issue was assigned to
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if assigned_to and assigned_to.email_address:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'issue_description': issue.description[:200] + '...' if len(issue.description) > 200 else issue.description,
                    'issue_type': issue.get_issue_type_display(),
                    'priority': issue.get_priority_display(),
                    'reported_by_name': issue.reported_by.name,
                })
                
                sender = AccountEmailSender(
                    recipients=[assigned_to.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_ASSIGNMENT type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue assignment notification: {e}")
            return False
    
    @staticmethod
    def send_issue_escalation_notification(issue):
        """
        Send a notification when an issue is escalated.
        
        Args:
            issue: The issue ticket object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            # Get cluster admins to notify about escalation
            from accounts.models import AccountUser
            cluster_admins = AccountUser.objects.filter(
                clusters=issue.cluster,
                is_cluster_admin=True
            )
            
            admin_emails = [admin.email_address for admin in cluster_admins if admin.email_address]
            
            if admin_emails:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'issue_description': issue.description[:200] + '...' if len(issue.description) > 200 else issue.description,
                    'issue_type': issue.get_issue_type_display(),
                    'priority': issue.get_priority_display(),
                    'reported_by_name': issue.reported_by.name,
                    'days_open': (timezone.now() - issue.created_at).days,
                })
                
                sender = AccountEmailSender(
                    recipients=admin_emails,
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_ESCALATION type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue escalation notification: {e}")
            return False
    
    @staticmethod
    def send_issue_due_reminder(issue):
        """
        Send a reminder when an issue is approaching its due date.
        
        Args:
            issue: The issue ticket object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if issue.assigned_to and issue.assigned_to.email_address:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'due_date': issue.due_date.strftime('%Y-%m-%d %H:%M') if issue.due_date else 'Not set',
                    'priority': issue.get_priority_display(),
                    'reported_by_name': issue.reported_by.name,
                })
                
                sender = AccountEmailSender(
                    recipients=[issue.assigned_to.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_DUE_REMINDER type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue due reminder: {e}")
            return False
    
    @staticmethod
    def send_issue_auto_close_notification(issue):
        """
        Send a notification when an issue is automatically closed.
        
        Args:
            issue: The issue ticket object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if issue.reported_by and issue.reported_by.email_address:
                context = Context({
                    'issue_number': issue.issue_no,
                    'issue_title': issue.title,
                    'resolved_date': issue.resolved_at.strftime('%Y-%m-%d %H:%M') if issue.resolved_at else 'Unknown',
                    'closed_date': issue.closed_at.strftime('%Y-%m-%d %H:%M') if issue.closed_at else 'Unknown',
                })
                
                sender = AccountEmailSender(
                    recipients=[issue.reported_by.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need ISSUE_AUTO_CLOSE type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send issue auto-close notification: {e}")
            return False
    
    @staticmethod
    def send_exit_request_notification(exit_request):
        """
        Send a notification when a new exit request is created.
        
        Args:
            exit_request: The exit request object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            # Get cluster admins to notify about the exit request
            from accounts.models import AccountUser
            cluster_admins = AccountUser.objects.filter(
                clusters=exit_request.cluster,
                is_cluster_admin=True
            )
            
            admin_emails = [admin.email_address for admin in cluster_admins if admin.email_address]
            
            if admin_emails:
                context = Context({
                    'request_id': exit_request.request_id,
                    'child_name': exit_request.child.name,
                    'parent_name': exit_request.requested_by.name,
                    'reason': exit_request.reason,
                    'expected_return_time': exit_request.expected_return_time.strftime('%Y-%m-%d %H:%M'),
                    'destination': exit_request.destination,
                    'accompanying_adult': exit_request.accompanying_adult,
                })
                
                sender = AccountEmailSender(
                    recipients=admin_emails,
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need EXIT_REQUEST type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send exit request notification: {e}")
            return False
    
    @staticmethod
    def send_exit_request_approved_notification(exit_request):
        """
        Send a notification when an exit request is approved.
        
        Args:
            exit_request: The exit request object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if exit_request.requested_by and exit_request.requested_by.email_address:
                context = Context({
                    'request_id': exit_request.request_id,
                    'child_name': exit_request.child.name,
                    'approved_by_name': exit_request.approved_by.name,
                    'expected_return_time': exit_request.expected_return_time.strftime('%Y-%m-%d %H:%M'),
                })
                
                sender = AccountEmailSender(
                    recipients=[exit_request.requested_by.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need EXIT_REQUEST_APPROVED type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send exit request approved notification: {e}")
            return False
    
    @staticmethod
    def send_exit_request_denied_notification(exit_request):
        """
        Send a notification when an exit request is denied.
        
        Args:
            exit_request: The exit request object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if exit_request.requested_by and exit_request.requested_by.email_address:
                context = Context({
                    'request_id': exit_request.request_id,
                    'child_name': exit_request.child.name,
                    'denied_by_name': exit_request.denied_by.name,
                    'denial_reason': exit_request.denial_reason,
                })
                
                sender = AccountEmailSender(
                    recipients=[exit_request.requested_by.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need EXIT_REQUEST_DENIED type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send exit request denied notification: {e}")
            return False
    
    @staticmethod
    def send_child_exit_notification(entry_exit_log):
        """
        Send a notification when a child exits the estate.
        
        Args:
            entry_exit_log: The entry/exit log object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if entry_exit_log.child.parent and entry_exit_log.child.parent.email_address:
                context = Context({
                    'child_name': entry_exit_log.child.name,
                    'exit_time': entry_exit_log.exit_time.strftime('%H:%M') if entry_exit_log.exit_time else 'Unknown',
                    'expected_return_time': entry_exit_log.expected_return_time.strftime('%Y-%m-%d %H:%M') if entry_exit_log.expected_return_time else 'Not specified',
                    'destination': entry_exit_log.destination,
                    'accompanying_adult': entry_exit_log.accompanying_adult,
                })
                
                sender = AccountEmailSender(
                    recipients=[entry_exit_log.child.parent.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need CHILD_EXIT type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send child exit notification: {e}")
            return False
    
    @staticmethod
    def send_child_entry_notification(entry_exit_log):
        """
        Send a notification when a child returns to the estate.
        
        Args:
            entry_exit_log: The entry/exit log object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            if entry_exit_log.child.parent and entry_exit_log.child.parent.email_address:
                context = Context({
                    'child_name': entry_exit_log.child.name,
                    'entry_time': entry_exit_log.entry_time.strftime('%H:%M') if entry_exit_log.entry_time else 'Unknown',
                    'duration_minutes': entry_exit_log.duration_minutes,
                })
                
                sender = AccountEmailSender(
                    recipients=[entry_exit_log.child.parent.email_address],
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need CHILD_ENTRY type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send child entry notification: {e}")
            return False
    
    @staticmethod
    def send_child_overdue_notification(entry_exit_log):
        """
        Send a notification when a child is overdue for return.
        
        Args:
            entry_exit_log: The entry/exit log object
        
        Returns:
            True if the notification was sent successfully, False otherwise
        """
        try:
            recipients = []
            
            # Notify the parent
            if entry_exit_log.child.parent and entry_exit_log.child.parent.email_address:
                recipients.append(entry_exit_log.child.parent.email_address)
            
            # Notify cluster admins
            from accounts.models import AccountUser
            cluster_admins = AccountUser.objects.filter(
                clusters=entry_exit_log.cluster,
                is_cluster_admin=True
            )
            
            admin_emails = [admin.email_address for admin in cluster_admins if admin.email_address]
            recipients.extend(admin_emails)
            
            if recipients:
                from django.utils import timezone
                overdue_minutes = int((timezone.now() - entry_exit_log.expected_return_time).total_seconds() / 60)
                
                context = Context({
                    'child_name': entry_exit_log.child.name,
                    'parent_name': entry_exit_log.child.parent.name,
                    'expected_return_time': entry_exit_log.expected_return_time.strftime('%Y-%m-%d %H:%M'),
                    'overdue_minutes': overdue_minutes,
                    'destination': entry_exit_log.destination,
                    'accompanying_adult': entry_exit_log.accompanying_adult,
                    'parent_phone': entry_exit_log.child.parent.phone_number,
                })
                
                sender = AccountEmailSender(
                    recipients=recipients,
                    email_type=NotificationTypes.VISITOR_ARRIVAL,  # Placeholder - would need CHILD_OVERDUE type
                    context=context
                )
                
                return sender.send()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send child overdue notification: {e}")
            return False