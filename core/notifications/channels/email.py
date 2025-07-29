'''
Email notification channel implementation for ClustR notification system.

This module implements the EmailChannel class that handles email notifications
using the existing AccountEmailSender infrastructure while providing clean
integration with the new notification system.
'''

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

from django.template import Context
from django.contrib.auth import get_user_model

from core.notifications.channels.base import BaseNotificationChannel
from core.notifications.events import NotificationEvent, NotificationEvents
from core.common.models.cluster import Cluster
from core.common.email_sender import AccountEmailSender, NotificationTypes
from accounts.models.user_settings import UserSettings

User = get_user_model()
logger = logging.getLogger(__name__)

# Dataclass-based context models for validation and transformation

@dataclass
class BaseEmailContext:
    """Base context model with common email formatting."""
    cluster_name: Optional[str] = None
    user_name: Optional[str] = None
    current_time: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC'))

    def __post_init__(self):
        # Allow for additional fields not defined in the dataclass
        pass

@dataclass
class VisitorEmailContext(BaseEmailContext):
    """Context model for visitor-related notifications."""
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    formatted_arrival_time: Optional[str] = None
    formatted_departure_time: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.arrival_time and not self.formatted_arrival_time:
            self.formatted_arrival_time = self.arrival_time.strftime('%H:%M on %B %d, %Y')
        if self.departure_time and not self.formatted_departure_time:
            self.formatted_departure_time = self.departure_time.strftime('%H:%M on %B %d, %Y')

@dataclass
class PaymentEmailContext(BaseEmailContext):
    """Context model for payment-related notifications."""
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    formatted_amount: Optional[str] = None
    formatted_due_date: Optional[str] = None
    days_until_due: Optional[int] = None
    days_overdue: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        if self.amount is not None and not self.formatted_amount:
            self.formatted_amount = f"${self.amount:.2f}"
        if self.due_date and not self.formatted_due_date:
            self.formatted_due_date = self.due_date.strftime('%B %d, %Y')
        if self.due_date:
            now = datetime.now(timezone.utc)
            # Ensure due_date is timezone-aware
            if self.due_date.tzinfo is None:
                self.due_date = self.due_date.replace(tzinfo=timezone.utc)
            delta = (self.due_date - now).days
            if delta > 0:
                self.days_until_due = delta
            elif delta < 0:
                self.days_overdue = abs(delta)

@dataclass
class PaymentReceiptEmailContext(BaseEmailContext):
    """Context model for payment receipt notifications."""
    payment_amount: Optional[float] = None
    remaining_amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    formatted_payment_amount: Optional[str] = None
    formatted_remaining_amount: Optional[str] = None
    formatted_payment_date: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.payment_amount is not None and not self.formatted_payment_amount:
            self.formatted_payment_amount = f"${self.payment_amount:.2f}"
        if self.remaining_amount is not None and not self.formatted_remaining_amount:
            self.formatted_remaining_amount = f"${self.remaining_amount:.2f}"
        if self.payment_date and not self.formatted_payment_date:
            self.formatted_payment_date = self.payment_date.strftime('%B %d, %Y at %H:%M')

@dataclass
class EmergencyEmailContext(BaseEmailContext):
    """Context model for emergency notifications."""
    alert_time: Optional[datetime] = None
    severity: Optional[str] = None
    formatted_alert_time: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.alert_time and not self.formatted_alert_time:
            self.formatted_alert_time = self.alert_time.strftime('%H:%M on %B %d, %Y')
        if self.severity:
            self.severity = str(self.severity).upper()


class EmailChannel(BaseNotificationChannel):
    """
    Email notification channel implementation.
    """
    
    EVENT_EMAIL_TYPE_MAPPING = {
        NotificationEvents.EMERGENCY_ALERT.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.EMERGENCY_STATUS_CHANGED.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.SECURITY_BREACH.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.VISITOR_ARRIVAL.value: NotificationTypes.VISITOR_ARRIVAL,
        NotificationEvents.VISITOR_OVERSTAY.value: NotificationTypes.VISITOR_OVERSTAY,
        NotificationEvents.MAINTENANCE_URGENT.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.CHILD_EXIT_ALERT.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.CHILD_ENTRY_ALERT.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.CHILD_OVERDUE_ALERT.value: NotificationTypes.EMERGENCY_ALERT,
        NotificationEvents.PAYMENT_DUE.value: NotificationTypes.BILL_REMINDER,
        NotificationEvents.PAYMENT_OVERDUE.value: NotificationTypes.BILL_REMINDER,
        NotificationEvents.PAYMENT_CONFIRMED.value: NotificationTypes.PAYMENT_RECEIPT,
        NotificationEvents.ANNOUNCEMENT_POSTED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.ISSUE_ASSIGNED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.ISSUE_STATUS_CHANGED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.ISSUE_ESCALATED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.ISSUE_OVERDUE.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.ISSUE_AUTO_ESCALATED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.TASK_DUE.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.MAINTENANCE_SCHEDULED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.MAINTENANCE_COMPLETED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.BILL_CANCELLED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.BILL_ACKNOWLEDGED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.BILL_DISPUTED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_FAILED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_PAUSED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_RESUMED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_CANCELLED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_UPDATED.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.PAYMENT_SETUP.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.COMMENT_REPLY.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.NEWSLETTER.value: NotificationTypes.ANNOUNCEMENT,
        NotificationEvents.SYSTEM_UPDATE.value: NotificationTypes.ANNOUNCEMENT,
    }

    CONTEXT_MODELS = {
        NotificationEvents.VISITOR_ARRIVAL.value: VisitorEmailContext,
        NotificationEvents.VISITOR_OVERSTAY.value: VisitorEmailContext,
        NotificationEvents.PAYMENT_DUE.value: PaymentEmailContext,
        NotificationEvents.PAYMENT_OVERDUE.value: PaymentEmailContext,
        NotificationEvents.PAYMENT_CONFIRMED.value: PaymentReceiptEmailContext,
        NotificationEvents.EMERGENCY_ALERT.value: EmergencyEmailContext,
    }
    
    def send(
        self,
        event: NotificationEvent,
        recipients: List[User],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> bool:
        """
        Send email notification using existing infrastructure.
        """
        try:
            email_type = self.EVENT_EMAIL_TYPE_MAPPING.get(event.name)
            if not email_type:
                logger.error(f"No email template mapping for event: {event.name}")
                return False
            
            filtered_recipients = self.filter_recipients_by_preferences(recipients, event, cluster)
            valid_recipients = self.validate_recipients(filtered_recipients)
            
            if not valid_recipients:
                logger.info(f"No valid email recipients for event: {event.name}")
                return True
            
            email_context = self.transform_context(context, event, cluster)
            
            email_addresses = [user.email_address for user in valid_recipients]
            
            sender = AccountEmailSender(
                recipients=email_addresses,
                email_type=email_type,
                context=Context(email_context)
            )
            
            success = sender.send()
            
            for recipient in recipients:
                was_sent = recipient in valid_recipients
                error_msg = None if was_sent else "Recipient filtered out or invalid email"
                
                self.log_notification_attempt(
                    event=event,
                    recipient=recipient,
                    cluster=cluster,
                    success=success and was_sent,
                    context=context,
                    error_message=error_msg if not (success and was_sent) else None
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            
            for recipient in recipients:
                self.log_notification_attempt(
                    event=event,
                    recipient=recipient,
                    cluster=cluster,
                    success=False,
                    context=context,
                    error_message=str(e)
                )
            
            return False
    
    def filter_recipients_by_preferences(
        self,
        recipients: List[User],
        event: NotificationEvent,
        cluster: Cluster
    ) -> List[User]:
        """
        Filter recipients based on their email notification preferences.
        """
        if event.bypasses_preferences:
            logger.info(f"Critical event {event.name} bypassing user preferences")
            return recipients
        
        filtered_recipients = []
        
        for user in recipients:
            try:
                settings, _ = UserSettings.objects.get_or_create(user=user)
                if settings.get_notification_preference(event.name, 'EMAIL'):
                    filtered_recipients.append(user)
                else:
                    logger.debug(f"User {user.email_address} has disabled email notifications for {event.name}")
                    
            except Exception as e:
                logger.error(f"Error checking preferences for user {user.email_address}: {str(e)}")
                filtered_recipients.append(user)
        
        logger.info(f"Filtered {len(recipients)} recipients to {len(filtered_recipients)} for event {event.name}")
        return filtered_recipients
    
    def transform_context(
        self,
        base_context: dict[str, Any],
        event: NotificationEvent,
        cluster: Cluster
    ) -> dict[str, Any]:
        """
        Transform base context for email-specific formatting.
        """
        context_model_cls = self.CONTEXT_MODELS.get(event.name, BaseEmailContext)

        # Prepare initial data for dataclass instantiation
        initial_data = base_context.copy()
        if 'cluster' in initial_data and not initial_data.get('cluster_name'):
            initial_data['cluster_name'] = initial_data['cluster'].name
        if 'user' in initial_data and not initial_data.get('user_name'):
            initial_data['user_name'] = initial_data['user'].name

        # Filter out keys not present in the dataclass fields
        cls_fields = {f.name for f in fields(context_model_cls)}
        filtered_data = {k: v for k, v in initial_data.items() if k in cls_fields}

        try:
            context_instance = context_model_cls(**filtered_data)
            return asdict(context_instance)
        except TypeError as e:
            logger.error(f"Error instantiating context model for event {event.name}: {e}")
            return initial_data

    def validate_recipients(self, recipients: List[User]) -> List[User]:
        """
        Validate and filter recipients for email delivery.
        """
        valid_recipients = []
        
        for user in recipients:
            if hasattr(user, 'email_address') and user.email_address and '@' in user.email_address:
                valid_recipients.append(user)
            else:
                logger.warning(f"User {user.id} has an invalid or missing email address")
        
        return valid_recipients
    
    def get_channel_name(self) -> str:
        """
        Get the name of this channel for logging purposes.
        """
        return "EMAIL"
