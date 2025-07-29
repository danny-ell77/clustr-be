"""
Base notification channel interface for ClustR notification system.

This module defines the abstract base class that all notification channels
must implement to ensure consistent behavior across different delivery methods.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from django.contrib.auth import get_user_model

from core.notifications.events import NotificationEvent
from core.common.models.cluster import Cluster

User = get_user_model()


class BaseNotificationChannel(ABC):
    """
    Abstract base class for all notification channels.
    
    This class defines the interface that all notification channels (Email, SMS, 
    WebSocket, App) must implement. It ensures consistent behavior and provides
    a framework for preference filtering and context transformation.
    
    Each channel is responsible for:
    1. Filtering recipients based on user preferences
    2. Transforming context data for channel-specific needs
    3. Sending notifications through the appropriate delivery method
    4. Logging notification attempts for audit purposes
    """
    
    @abstractmethod
    def send(
        self,
        event: NotificationEvent,
        recipients: List[User],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> bool:
        """
        Send notification via this channel.
        
        This is the main entry point for sending notifications. Each channel
        implementation must handle the complete flow from preference filtering
        to actual delivery.
        
        Args:
            event: NotificationEvent object containing event metadata
            recipients: List of users to notify
            cluster: Cluster context for multi-tenant isolation
            context: Base context data for the notification
            
        Returns:
            True if all notifications sent successfully, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement send() method")
    
    @abstractmethod
    def filter_recipients_by_preferences(
        self,
        recipients: List[User],
        event: NotificationEvent,
        cluster: Cluster
    ) -> List[User]:
        """
        Filter recipients based on their notification preferences.
        
        This method should check user preferences for the specific event type
        and channel, unless the event bypasses preferences (critical events).
        
        Args:
            recipients: List of users to filter
            event: NotificationEvent object
            cluster: Cluster context for preference lookup
            
        Returns:
            Filtered list of users who should receive the notification
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement filter_recipients_by_preferences() method")
    
    @abstractmethod
    def transform_context(
        self,
        base_context: dict[str, Any],
        event: NotificationEvent
    ) -> dict[str, Any]:
        """
        Transform base context data for channel-specific formatting.
        
        Each channel may need different formatting for the same data.
        For example, email might need formatted dates and currency,
        while SMS might need abbreviated text.
        
        Args:
            base_context: Original context data
            event: NotificationEvent object for context-aware transformations
            
        Returns:
            Transformed context dictionary suitable for this channel
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement transform_context() method")
    
    @abstractmethod
    def validate_recipients(
        self,
        recipients: List[User]
    ) -> List[User]:
        """
        Validate and filter recipients for this channel.
        
        Each channel should validate that recipients have the necessary
        contact information (email address, phone number, etc.) and
        filter out invalid recipients.
        
        Args:
            recipients: List of users to validate
            
        Returns:
            List of valid recipients for this channel
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement validate_recipients() method")
    
    def log_notification_attempt(
        self,
        event: NotificationEvent,
        recipient: User,
        cluster: Cluster,
        success: bool,
        context: dict[str, Any],
        error_message: Optional[str] = None
    ) -> None:
        """
        Log notification attempt for audit purposes.
        
        This is a concrete method that all channels can use to log
        notification attempts. It creates a NotificationLog entry
        for tracking and debugging purposes.
        
        Args:
            event: NotificationEvent object
            recipient: User who received (or should have received) the notification
            cluster: Cluster context
            success: Whether the notification was sent successfully
            context: Context data used for the notification
            error_message: Error message if notification failed
        """
        from core.notifications.models import NotificationLog
        
        NotificationLog.objects.create(
            cluster=cluster,
            event=event.name,
            recipient=recipient,
            channel=self.get_channel_name(),
            success=success,
            error_message=error_message,
            context_data=context
        )
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Get the name of this channel for logging purposes.
        
        Returns:
            String name of the channel (e.g., "EMAIL", "SMS", "WEBSOCKET")
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_channel_name() method")
    
    def supports_event(self, event: NotificationEvent) -> bool:
        """
        Check if this channel supports the given event.
        
        This is a helper method that checks if the event's supported_channels
        list includes this channel type.
        
        Args:
            event: NotificationEvent to check
            
        Returns:
            True if channel supports the event, False otherwise
        """
        from core.notifications.events import NotificationChannel
        
        # Get the channel enum value for this channel
        channel_name = self.get_channel_name().lower()
        try:
            channel_enum = NotificationChannel(channel_name)
            return event.supports_channel(channel_enum)
        except ValueError:
            # Channel name not found in enum
            return False
    
    def get_preference_key(self, event: NotificationEvent) -> str:
        """
        Get the preference key for this event and channel combination.
        
        This helper method generates a consistent preference key that can
        be used to look up user preferences in the UserSettings model.
        
        Args:
            event: NotificationEvent object
            
        Returns:
            String preference key (e.g., "visitor_arrival_email")
        """
        channel_name = self.get_channel_name().lower()
        return f"{event.name}_{channel_name}"
    
    def handle_send_error(
        self,
        error: Exception,
        event: NotificationEvent,
        recipient: User,
        cluster: Cluster,
        context: dict[str, Any]
    ) -> None:
        """
        Handle errors that occur during notification sending.
        
        This helper method provides consistent error handling across
        all channels, including logging and error reporting.
        
        Args:
            error: Exception that occurred
            event: NotificationEvent object
            recipient: User who should have received the notification
            cluster: Cluster context
            context: Context data used for the notification
        """
        import logging
        
        logger = logging.getLogger(__name__)
        
        error_message = f"{type(error).__name__}: {str(error)}"
        
        # Log the error
        logger.error(
            f"Failed to send {event.name} notification to {recipient.email_address} "
            f"via {self.get_channel_name()}: {error_message}"
        )
        
        # Log to database for audit
        self.log_notification_attempt(
            event=event,
            recipient=recipient,
            cluster=cluster,
            success=False,
            context=context,
            error_message=error_message
        )