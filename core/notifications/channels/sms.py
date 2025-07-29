"""
SMS notification channel implementation for ClustR notification system.

This module implements the SmsChannel class that handles SMS notifications.
"""

import logging
from typing import List, Any, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model

from core.common.models.cluster import Cluster
from core.notifications.channels.base import BaseNotificationChannel
from core.notifications.events import NotificationEvent, NotificationEvents
from accounts.models.user_settings import UserSettings
from accounts.models.sms_sender import SMSSender

if TYPE_CHECKING:
    User = get_user_model()

logger = logging.getLogger(__name__)


# Dataclass models for context validation and transformation
@dataclass
class BaseSmsContext:
    """Base context model for SMS notifications."""

    cluster_name: str


@dataclass
class EmergencySmsContext(BaseSmsContext):
    """Context for emergency alerts."""

    severity: str
    message: str
    alert_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    formatted_alert_time: str = ""

    def __post_init__(self):
        """Format alert time after initialization."""
        if self.alert_time:
            self.formatted_alert_time = self.alert_time.strftime("%H:%M %Z on %b %d")


@dataclass
class VisitorSmsContext(BaseSmsContext):
    """Context for visitor notifications."""

    visitor_name: str
    arrival_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    formatted_arrival_time: str = ""

    def __post_init__(self):
        """Format arrival time after initialization."""
        if self.arrival_time:
            self.formatted_arrival_time = self.arrival_time.strftime("%H:%M")


@dataclass
class PaymentSmsContext(BaseSmsContext):
    """Context for payment notifications."""

    amount: float
    due_date: datetime
    formatted_amount: str = ""
    formatted_due_date: str = ""

    def __post_init__(self):
        """Format amount and due date after initialization."""
        if self.amount is not None:
            self.formatted_amount = f"${self.amount:.2f}"
        if self.due_date:
            self.formatted_due_date = self.due_date.strftime("%b %d, %Y")


class SmsChannel(BaseNotificationChannel):
    """
    SMS notification channel implementation.
    """

    SMS_TEMPLATES = {
        NotificationEvents.EMERGENCY_ALERT.value: "ClustR Emergency [{severity}]: {message} in {cluster_name} at {formatted_alert_time}.",
        NotificationEvents.SECURITY_BREACH.value: "ClustR Security Alert: A security breach has been detected in {cluster_name}. Please be vigilant.",
        NotificationEvents.VISITOR_ARRIVAL.value: "ClustR Alert: Your visitor, {visitor_name}, arrived at {formatted_arrival_time}.",
        NotificationEvents.VISITOR_OVERSTAY.value: "ClustR Alert: Your visitor, {visitor_name}, has overstayed their welcome in {cluster_name}.",
        NotificationEvents.MAINTENANCE_URGENT.value: "ClustR Urgent Maintenance: {message} in {cluster_name}.",
        NotificationEvents.CHILD_EXIT_ALERT.value: "ClustR Child Safety Alert: {child_name} has exited {location} at {time} in {cluster_name}.",
        NotificationEvents.CHILD_ENTRY_ALERT.value: "ClustR Child Safety Alert: {child_name} has entered {location} at {time} in {cluster_name}.",
        NotificationEvents.CHILD_OVERDUE_ALERT.value: "ClustR Child Safety Alert: {child_name} is overdue for return to {location} in {cluster_name}.",
        NotificationEvents.PAYMENT_OVERDUE.value: "ClustR Payment Reminder: Your payment of {formatted_amount} for {cluster_name} is overdue. Due date was {formatted_due_date}.",
    }

    CONTEXT_MODELS = {
        NotificationEvents.EMERGENCY_ALERT.value: EmergencySmsContext,
        NotificationEvents.VISITOR_ARRIVAL.value: VisitorSmsContext,
        NotificationEvents.PAYMENT_OVERDUE.value: PaymentSmsContext,
    }

    def send(
        self,
        event: NotificationEvent,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """
        Send SMS notification.
        """
        template = self.SMS_TEMPLATES.get(event.name)
        if not template:
            logger.info(f"No SMS template for event: {event.name}")
            return True

        try:
            transformed_context = self.transform_context(context, event, cluster)

            filtered_recipients = self.filter_recipients_by_preferences(
                recipients, event, cluster
            )
            valid_recipients = self.validate_recipients(filtered_recipients)

            if not valid_recipients:
                logger.info(f"No valid SMS recipients for event: {event.name}")
                return True

            all_success = True
            for recipient in valid_recipients:
                message_body = template.format(**transformed_context)
                success = SMSSender.send_sms(recipient.phone_number, message_body)
                if not success:
                    all_success = False

                self.log_notification_attempt(
                    event=event,
                    recipient=recipient,
                    cluster=cluster,
                    success=success,
                    context=transformed_context,
                    error_message=None if success else "Failed to send SMS",
                )

            return all_success

        except Exception as e:
            logger.error(
                f"Error sending SMS notification for event {event.name}: {str(e)}"
            )
            for recipient in recipients:
                self.log_notification_attempt(
                    event=event,
                    recipient=recipient,
                    cluster=cluster,
                    success=False,
                    context=context,
                    error_message=str(e),
                )
            return False

    def transform_context(
        self, base_context: dict[str, Any], event: NotificationEvent, cluster: Cluster
    ) -> dict[str, Any]:
        """
        Validate and transform context for SMS templates.
        """
        context_model = self.CONTEXT_MODELS.get(event.name)
        if not context_model:
            return base_context

        # Add cluster_name to the context
        context_with_cluster = {**base_context, "cluster_name": cluster.name}

        try:
            validated_context = context_model(**context_with_cluster)
            return validated_context.__dict__
        except Exception as e:
            logger.error(f"Context validation failed for event {event.name}: {e}")
            # Fallback to base context
            return context_with_cluster

    def filter_recipients_by_preferences(
        self, recipients: List["User"], event: NotificationEvent, cluster: Cluster
    ) -> List["User"]:
        """
        Filter recipients based on their SMS notification preferences.
        """
        if event.bypasses_preferences:
            logger.info(
                f"Critical event {event.name} bypassing user preferences for SMS"
            )
            return recipients

        filtered_recipients = []
        for user in recipients:
            try:
                settings, _ = UserSettings.objects.get_or_create(user=user)
                if settings.get_notification_preference(event.name, "SMS"):
                    filtered_recipients.append(user)
                else:
                    logger.debug(
                        f"User {user.id} has disabled SMS notifications for {event.name}"
                    )
            except Exception as e:
                logger.error(
                    f"Error checking SMS preferences for user {user.id}: {str(e)}"
                )
                filtered_recipients.append(user)

        logger.info(
            f"Filtered {len(recipients)} recipients to {len(filtered_recipients)} for SMS event {event.name}"
        )
        return filtered_recipients

    def validate_recipients(self, recipients: List["User"]) -> List["User"]:
        """
        Validate and filter recipients for SMS delivery.
        """
        valid_recipients = []
        for user in recipients:
            if hasattr(user, "phone_number") and user.phone_number:
                valid_recipients.append(user)
            else:
                logger.warning(f"User {user.id} has no phone number")
        return valid_recipients

    def get_channel_name(self) -> str:
        """
        Get the name of this channel for logging purposes.
        """
        return "SMS"
