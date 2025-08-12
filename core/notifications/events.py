"""
Notification events, priorities, and channels for the ClustR notification system.

This module defines the core enums and constants used throughout the notification system
to ensure type safety and prevent typos in event names.
"""

from enum import Enum, IntEnum
from typing import List


class NotificationPriority(IntEnum):
    """Priority levels for notifications. Lower numbers indicate higher priority."""
    CRITICAL = 1    # Bypasses user preferences
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    SMS = "sms"
    WEBSOCKET = "websocket"
    APP = "app"


class NotificationEvents(Enum):
    """Enum for notification event names to prevent typos and ensure consistency."""
    
    # Critical events (bypass user preferences)
    EMERGENCY_ALERT = "emergency_alert"
    EMERGENCY_STATUS_CHANGED = "emergency_status_changed"
    SECURITY_BREACH = "security_breach"
    
    # High priority events
    VISITOR_ARRIVAL = "visitor_arrival"
    VISITOR_OVERSTAY = "visitor_overstay"
    MAINTENANCE_URGENT = "maintenance_urgent"
    CHILD_EXIT_ALERT = "child_exit_alert"
    CHILD_ENTRY_ALERT = "child_entry_alert"
    CHILD_OVERDUE_ALERT = "child_overdue_alert"
    
    # Medium priority events
    PAYMENT_DUE = "payment_due"
    PAYMENT_OVERDUE = "payment_overdue"
    PAYMENT_CONFIRMED = "payment_confirmed"
    ANNOUNCEMENT_POSTED = "announcement_posted"
    EXIT_REQUEST_REMINDER = "exit_request_reminder"
    ISSUE_ASSIGNED = "issue_assigned"
    ISSUE_STATUS_CHANGED = "issue_status_changed"
    ISSUE_ESCALATED = "issue_escalated"
    ISSUE_OVERDUE = "issue_overdue"
    ISSUE_AUTO_ESCALATED = "issue_auto_escalated"
    TASK_DUE = "task_due"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    BILL_CREATED = "bill_created"
    BILL_OVERDUE = "bill_overdue"
    BILL_REMINDER = "bill_reminder"
    BILL_STATUS_CHANGED = "bill_status_changed"
    BILL_CANCELLED = "bill_cancelled"
    BILL_ACKNOWLEDGED = "bill_acknowledged"
    BILL_DISPUTED = "bill_disputed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_PAUSED = "payment_paused"
    PAYMENT_RESUMED = "payment_resumed"
    PAYMENT_CANCELLED = "payment_cancelled"
    PAYMENT_UPDATED = "payment_updated"
    PAYMENT_SETUP = "payment_setup"
    PAYMENT_SUCCESSFUL = "payment_successful"
    RECURRING_PAYMENT_REMINDER = "recurring_payment_reminder"
    SHIFT_ASSIGNED = "shift_assigned"
    SHIFT_REMINDER = "shift_reminder"
    SHIFT_MISSED = "shift_missed"
    SHIFT_SWAP_REQUEST = "shift_swap_request"
    SHIFT_SWAP_RESPONSE = "shift_swap_response"
    MAINTENANCE_DUE = "maintenance_due"
    MAINTENANCE_REQUESTED = "maintenance_requested"
    
    # Low priority events
    COMMENT_ADDED = "comment_added"
    COMMENT_REPLY = "comment_reply"
    NEWSLETTER = "newsletter"
    SYSTEM_UPDATE = "system_update"


class NotificationEvent:
    """
    Clean abstraction for notification events with priority and channel information.
    
    This class encapsulates all the metadata about a notification event including
    its priority level, supported channels, and whether it bypasses user preferences.
    """
    
    def __init__(
        self, 
        name: str, 
        priority: NotificationPriority, 
        supported_channels: List[NotificationChannel]
    ):
        """
        Initialize a notification event.
        
        Args:
            name: The event name (should match the enum value)
            priority: Priority level from NotificationPriority enum
            supported_channels: List of channels that support this event
        """
        self.name = name
        self.priority = priority
        self.supported_channels = supported_channels
    
    @property
    def bypasses_preferences(self) -> bool:
        """
        Determine if this event bypasses user notification preferences.
        
        Critical events (priority = CRITICAL) bypass user preferences to ensure
        important safety and security notifications are always delivered.
        
        Returns:
            True if event bypasses user preferences, False otherwise
        """
        return self.priority == NotificationPriority.CRITICAL
    
    @property
    def priority_level(self) -> str:
        """
        Get human-readable priority level name.
        
        Returns:
            String representation of priority level (CRITICAL, HIGH, MEDIUM, LOW)
        """
        return self.priority.name
    
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """
        Check if this event supports a specific notification channel.
        
        Args:
            channel: The notification channel to check
            
        Returns:
            True if channel is supported, False otherwise
        """
        return channel in self.supported_channels


# Event registry - maps enum keys to event objects for easy lookup
NOTIFICATION_EVENTS = {
    # Critical events that bypass user preferences
    NotificationEvents.EMERGENCY_ALERT: NotificationEvent(
        name=NotificationEvents.EMERGENCY_ALERT.value,
        priority=NotificationPriority.CRITICAL,
        supported_channels=[
            NotificationChannel.EMAIL, 
            NotificationChannel.SMS, 
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    NotificationEvents.EMERGENCY_STATUS_CHANGED: NotificationEvent(
        name=NotificationEvents.EMERGENCY_STATUS_CHANGED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL, 
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.SECURITY_BREACH: NotificationEvent(
        name=NotificationEvents.SECURITY_BREACH.value,
        priority=NotificationPriority.CRITICAL,
        supported_channels=[
            NotificationChannel.EMAIL, 
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    # High priority events
    NotificationEvents.VISITOR_ARRIVAL: NotificationEvent(
        name=NotificationEvents.VISITOR_ARRIVAL.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL, 
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    NotificationEvents.VISITOR_OVERSTAY: NotificationEvent(
        name=NotificationEvents.VISITOR_OVERSTAY.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.MAINTENANCE_URGENT: NotificationEvent(
        name=NotificationEvents.MAINTENANCE_URGENT.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.CHILD_EXIT_ALERT: NotificationEvent(
        name=NotificationEvents.CHILD_EXIT_ALERT.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    NotificationEvents.CHILD_ENTRY_ALERT: NotificationEvent(
        name=NotificationEvents.CHILD_ENTRY_ALERT.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    NotificationEvents.CHILD_OVERDUE_ALERT: NotificationEvent(
        name=NotificationEvents.CHILD_OVERDUE_ALERT.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    # Medium priority events
    NotificationEvents.PAYMENT_DUE: NotificationEvent(
        name=NotificationEvents.PAYMENT_DUE.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_OVERDUE: NotificationEvent(
        name=NotificationEvents.PAYMENT_OVERDUE.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.PAYMENT_CONFIRMED: NotificationEvent(
        name=NotificationEvents.PAYMENT_CONFIRMED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.ANNOUNCEMENT_POSTED: NotificationEvent(
        name=NotificationEvents.ANNOUNCEMENT_POSTED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET,
            NotificationChannel.APP
        ]
    ),
    
    NotificationEvents.EXIT_REQUEST_REMINDER: NotificationEvent(
        name=NotificationEvents.EXIT_REQUEST_REMINDER.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.ISSUE_ASSIGNED: NotificationEvent(
        name=NotificationEvents.ISSUE_ASSIGNED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.ISSUE_STATUS_CHANGED: NotificationEvent(
        name=NotificationEvents.ISSUE_STATUS_CHANGED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.ISSUE_ESCALATED: NotificationEvent(
        name=NotificationEvents.ISSUE_ESCALATED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.ISSUE_OVERDUE: NotificationEvent(
        name=NotificationEvents.ISSUE_OVERDUE.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.ISSUE_AUTO_ESCALATED: NotificationEvent(
        name=NotificationEvents.ISSUE_AUTO_ESCALATED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.TASK_DUE: NotificationEvent(
        name=NotificationEvents.TASK_DUE.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.MAINTENANCE_SCHEDULED: NotificationEvent(
        name=NotificationEvents.MAINTENANCE_SCHEDULED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.MAINTENANCE_COMPLETED: NotificationEvent(
        name=NotificationEvents.MAINTENANCE_COMPLETED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.BILL_CREATED: NotificationEvent(
        name=NotificationEvents.BILL_CREATED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.BILL_OVERDUE: NotificationEvent(
        name=NotificationEvents.BILL_OVERDUE.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.BILL_REMINDER: NotificationEvent(
        name=NotificationEvents.BILL_REMINDER.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.BILL_STATUS_CHANGED: NotificationEvent(
        name=NotificationEvents.BILL_STATUS_CHANGED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.BILL_CANCELLED: NotificationEvent(
        name=NotificationEvents.BILL_CANCELLED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.BILL_ACKNOWLEDGED: NotificationEvent(
        name=NotificationEvents.BILL_ACKNOWLEDGED.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.BILL_DISPUTED: NotificationEvent(
        name=NotificationEvents.BILL_DISPUTED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.PAYMENT_FAILED: NotificationEvent(
        name=NotificationEvents.PAYMENT_FAILED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.PAYMENT_PAUSED: NotificationEvent(
        name=NotificationEvents.PAYMENT_PAUSED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_RESUMED: NotificationEvent(
        name=NotificationEvents.PAYMENT_RESUMED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_CANCELLED: NotificationEvent(
        name=NotificationEvents.PAYMENT_CANCELLED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_UPDATED: NotificationEvent(
        name=NotificationEvents.PAYMENT_UPDATED.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_SETUP: NotificationEvent(
        name=NotificationEvents.PAYMENT_SETUP.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.PAYMENT_SUCCESSFUL: NotificationEvent(
        name=NotificationEvents.PAYMENT_SUCCESSFUL.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.RECURRING_PAYMENT_REMINDER: NotificationEvent(
        name=NotificationEvents.RECURRING_PAYMENT_REMINDER.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.SHIFT_ASSIGNED: NotificationEvent(
        name=NotificationEvents.SHIFT_ASSIGNED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.SHIFT_REMINDER: NotificationEvent(
        name=NotificationEvents.SHIFT_REMINDER.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.SHIFT_MISSED: NotificationEvent(
        name=NotificationEvents.SHIFT_MISSED.value,
        priority=NotificationPriority.HIGH,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.SHIFT_SWAP_REQUEST: NotificationEvent(
        name=NotificationEvents.SHIFT_SWAP_REQUEST.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    NotificationEvents.SHIFT_SWAP_RESPONSE: NotificationEvent(
        name=NotificationEvents.SHIFT_SWAP_RESPONSE.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.MAINTENANCE_DUE: NotificationEvent(
        name=NotificationEvents.MAINTENANCE_DUE.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.SMS
        ]
    ),
    
    NotificationEvents.MAINTENANCE_REQUESTED: NotificationEvent(
        name=NotificationEvents.MAINTENANCE_REQUESTED.value,
        priority=NotificationPriority.MEDIUM,
        supported_channels=[
            NotificationChannel.EMAIL,
            NotificationChannel.WEBSOCKET
        ]
    ),
    
    # Low priority events
    NotificationEvents.COMMENT_ADDED: NotificationEvent(
        name=NotificationEvents.COMMENT_ADDED.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.COMMENT_REPLY: NotificationEvent(
        name=NotificationEvents.COMMENT_REPLY.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.NEWSLETTER: NotificationEvent(
        name=NotificationEvents.NEWSLETTER.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
    
    NotificationEvents.SYSTEM_UPDATE: NotificationEvent(
        name=NotificationEvents.SYSTEM_UPDATE.value,
        priority=NotificationPriority.LOW,
        supported_channels=[NotificationChannel.EMAIL]
    ),
}


def get_event(event_name: NotificationEvents) -> NotificationEvent:
    """
    Get a notification event by its enum key.
    
    Args:
        event_name: The notification event enum
        
    Returns:
        NotificationEvent object
        
    Raises:
        KeyError: If event is not found in registry
    """
    return NOTIFICATION_EVENTS[event_name]


def get_events_by_priority(priority: NotificationPriority) -> List[NotificationEvent]:
    """
    Get all events with a specific priority level.
    
    Args:
        priority: The priority level to filter by
        
    Returns:
        List of NotificationEvent objects with the specified priority
    """
    return [event for event in NOTIFICATION_EVENTS.values() if event.priority == priority]


def get_critical_events() -> List[NotificationEvent]:
    """
    Get all critical events that bypass user preferences.
    
    Returns:
        List of critical NotificationEvent objects
    """
    return [event for event in NOTIFICATION_EVENTS.values() if event.bypasses_preferences]