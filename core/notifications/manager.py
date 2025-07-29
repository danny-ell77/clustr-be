"""
NotificationManager - Central orchestrator for the ClustR notification system.

This module provides the main API for sending notifications across different channels
with proper event validation, channel routing, and error handling.
"""
import typing
import logging
from typing import List, Dict, Any, Optional

from django.contrib.auth import get_user_model

from core.notifications.events import NotificationEvents, NotificationEvent, NOTIFICATION_EVENTS, NotificationChannel
from core.common.models.cluster import Cluster

if typing.TYPE_CHECKING:
    User = get_user_model()

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Central orchestrator for the notification system.
    
    This class provides a clean, simple API for sending notifications while handling
    all the complexity of event validation, channel routing, preference checking,
    and error handling internally.
    
    Usage:
        NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[user1, user2],
            cluster=request.user.cluster,
            context={'visitor_name': 'John Doe', 'unit': 'A101'}
        )
    """
    
    @staticmethod
    def send(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> bool:
        """
        Send notification to recipients based on event type and user preferences.
        
        This is the main entry point for the notification system. It handles:
        1. Event validation and lookup
        2. Input validation (recipients, cluster)
        3. Channel routing and orchestration
        4. Error handling and logging
        
        Args:
            event_name: Notification event enum (from NotificationEvents)
            recipients: List of users to notify
            cluster: Cluster context for multi-tenancy
            context: Base context data that channels can transform as needed
            
        Returns:
            True if all notifications sent successfully, False otherwise
            
        Raises:
            ValueError: If event_name is not a valid NotificationEvents enum
            TypeError: If recipients is not a list or cluster is not a Cluster instance
        """
        self._run_safeguards(
            event_name,
            recipients,
            cluster,
            context,
        )
        # Send via supported channels - each channel handles its own preference filtering and context transformation
        overall_success = True
        channel_results = {}
        channel_errors = {}
        
        if not event.supported_channels:
            logger.warning(f"Event {event_name.value} has no supported channels configured")
            return True  # Not an error, just no channels to send to
        
        for channel in event.supported_channels:
            channel_name = channel.value
            
            try:
                logger.debug(
                    f"Sending {event_name.value} via {channel_name} channel to "
                    f"{len(recipients)} recipients in cluster {cluster.name}"
                )
                
                channel_success = NotificationManager._send_via_channel(
                    channel=channel,
                    event=event,
                    recipients=recipients,
                    cluster=cluster,
                    context=context
                )
                
                channel_results[channel_name] = channel_success
                overall_success = overall_success and channel_success
                
                if channel_success:
                    logger.debug(f"Successfully sent {event_name.value} via {channel_name}")
                else:
                    logger.warning(f"Failed to send {event_name.value} via {channel_name}")
                
            except ValueError as e:
                # Channel-specific validation errors
                error_msg = f"Validation error in {channel_name} channel: {str(e)}"
                logger.error(error_msg)
                channel_results[channel_name] = False
                channel_errors[channel_name] = error_msg
                overall_success = False
                
            except ImportError as e:
                # Channel implementation not available
                error_msg = f"Channel {channel_name} implementation not available: {str(e)}"
                logger.error(error_msg)
                channel_results[channel_name] = False
                channel_errors[channel_name] = error_msg
                overall_success = False
                
            except Exception as e:
                # Unexpected errors
                error_msg = f"Unexpected error in {channel_name} channel: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                channel_results[channel_name] = False
                channel_errors[channel_name] = error_msg
                overall_success = False
        
        # Log final results with detailed error information
        successful_channels = [ch for ch, success in channel_results.items() if success]
        failed_channels = [ch for ch, success in channel_results.items() if not success]
        
        if overall_success:
            logger.info(
                f"Successfully sent {event_name.value} notification to {len(recipients)} recipients "
                f"via all {len(successful_channels)} channels: {', '.join(successful_channels)}"
            )
        else:
            if successful_channels:
                logger.warning(
                    f"Partial success for {event_name.value} notification to {len(recipients)} recipients. "
                    f"Successful channels ({len(successful_channels)}): {', '.join(successful_channels)}. "
                    f"Failed channels ({len(failed_channels)}): {', '.join(failed_channels)}"
                )
                
                # Log specific errors for failed channels
                for channel_name in failed_channels:
                    if channel_name in channel_errors:
                        logger.error(f"Error in {channel_name}: {channel_errors[channel_name]}")
            else:
                logger.error(
                    f"All {len(failed_channels)} channels failed for {event_name.value} notification "
                    f"to {len(recipients)} recipients"
                )
                
                # Log all errors
                for channel_name, error_msg in channel_errors.items():
                    logger.error(f"Error in {channel_name}: {error_msg}")
        
        return overall_success

    def _run_safeguards(event_name: NotificationEvent, recipients: list["AccountUser"], cluster: "Cluster", context: dict[str, Any]):
        assert isinstance(event_name, NotificationEvents),  f"event_name must be a NotificationEvents enum, got {type(event_name).__name__}"
        
        assert isinstance(recipients, list),  f"recipients must be a list, got {type(recipients).__name__}"
        
        assert isinstance(cluster, Cluster), f"cluster must be a Cluster instance, got {type(cluster).__name__}"
        
        assert isinstance(context, dict),  f"context must be a dictionary, got {type(context).__name__}"
            
        # Get event definition
        event = NOTIFICATION_EVENTS.get(event_name)
        if not event:
            error_msg = f"Unknown event: {event_name}. Available events: {list(NOTIFICATION_EVENTS.keys())}"
            logger.error(error_msg)
            return False
        
        # Handle empty recipients list
        if not recipients:
            logger.info(f"No recipients provided for event: {event_name.value}")
            return True
        
        # Validate recipients list contains valid user objects
        try:
            invalid_recipients = []
            for i, recipient in enumerate(recipients):
                if not hasattr(recipient, 'email_address') or not hasattr(recipient, 'id'):
                    invalid_recipients.append(f"index {i}: {type(recipient).__name__}")
            
            if invalid_recipients:
                error_msg = f"Invalid recipients found: {', '.join(invalid_recipients)}"
                logger.error(f"Recipient validation failed for {event_name.value}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating recipients for {event_name.value}: {str(e)}")
            return False
        
        # Validate cluster
        try:
            if not cluster or not hasattr(cluster, 'id') or not cluster.id:
                error_msg = f"Invalid cluster provided: cluster must have a valid ID"
                logger.error(f"Cluster validation failed for {event_name.value}: {error_msg}")
                return False
            
            if not hasattr(cluster, 'name'):
                logger.warning(f"Cluster {cluster.id} missing name attribute for {event_name.value}")
                
        except Exception as e:
            logger.error(f"Error validating cluster for {event_name.value}: {str(e)}")
            return False
        
        # Validate notification context
        if not NotificationManager._validate_notification_context(context, event_name):
            logger.warning(f"Context validation issues detected for {event_name.value}, proceeding anyway")
        
        logger.info(
            f"Sending {event_name.value} notification to {len(recipients)} recipients "
            f"in cluster {cluster.name} (priority: {event.priority_level})"
        )
        
    
    @staticmethod
    def _send_via_channel(
        channel: NotificationChannel,
        event: NotificationEvent,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> bool:
        """
        Send notification via a specific channel.
        
        This method handles the instantiation and execution of specific channel
        implementations. It provides a clean separation between the manager
        and individual channels.
        
        Args:
            channel: NotificationChannel enum value
            event: NotificationEvent object
            recipients: List of users to notify
            cluster: Cluster context
            context: Context data for the notification
            
        Returns:
            True if channel sent successfully, False otherwise
        """
        channel_name = channel.value.upper()
        
        try:
            # Get channel instance
            channel_instance = NotificationManager._get_channel_instance(channel)
            
            if channel_instance is None:
                # Channel not implemented yet - log warning but don't fail
                logger.warning(f"{channel_name} channel not yet implemented for event: {event.name}")
                return True  # Don't fail overall notification for unimplemented channels
            
            # Validate that channel supports this event
            if not channel_instance.supports_event(event):
                logger.error(f"{channel_name} channel does not support event: {event.name}")
                return False
            
            # Send via the channel
            logger.debug(f"Sending {event.name} to {len(recipients)} recipients via {channel_name}")
            result = channel_instance.send(event, recipients, cluster, context)
            
            if result:
                logger.debug(f"Successfully sent {event.name} via {channel_name}")
            else:
                logger.warning(f"Channel {channel_name} reported failure for event: {event.name}")
            
            return result
            
        except ImportError as e:
            logger.error(f"Failed to import {channel_name} channel: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending via {channel_name} channel: {str(e)}")
            return False
    
    @staticmethod
    def _get_channel_instance(channel: NotificationChannel):
        """
        Get an instance of the specified channel.
        
        This method centralizes channel instantiation and makes it easier
        to add new channels in the future.
        
        Args:
            channel: NotificationChannel enum value
            
        Returns:
            Channel instance or None if not implemented
            
        Raises:
            ImportError: If channel module cannot be imported
        """
        if channel == NotificationChannel.EMAIL:
            from core.notifications.channels.email import EmailChannel
            return EmailChannel()
        elif channel == NotificationChannel.SMS:
            # Future implementation
            # from core.notifications.channels.sms import SMSChannel
            # return SMSChannel()
            return None
        elif channel == NotificationChannel.WEBSOCKET:
            # Future implementation
            # from core.notifications.channels.websocket import WebSocketChannel
            # return WebSocketChannel()
            return None
        elif channel == NotificationChannel.APP:
            # Future implementation
            # from core.notifications.channels.app import AppChannel
            # return AppChannel()
            return None
        else:
            logger.error(f"Unknown channel: {channel}")
            return None
    
    @staticmethod
    def get_event_info(event_name: NotificationEvents) -> Optional[NotificationEvent]:
        """
        Get information about a specific notification event.
        
        This is a utility method for inspecting event properties without
        sending notifications.
        
        Args:
            event_name: NotificationEvents enum value
            
        Returns:
            NotificationEvent object if found, None otherwise
        """
        return NOTIFICATION_EVENTS.get(event_name)
    
    @staticmethod
    def validate_event_exists(event_name: NotificationEvents) -> bool:
        """
        Validate that an event exists in the registry.
        
        Args:
            event_name: NotificationEvents enum value
            
        Returns:
            True if event exists, False otherwise
        """
        return event_name in NOTIFICATION_EVENTS
    
    @staticmethod
    def get_supported_channels(event_name: NotificationEvents) -> List[NotificationChannel]:
        """
        Get the list of channels that support a specific event.
        
        Args:
            event_name: NotificationEvents enum value
            
        Returns:
            List of NotificationChannel enums, empty list if event not found
        """
        event = NOTIFICATION_EVENTS.get(event_name)
        return event.supported_channels if event else []
    
    @staticmethod
    def is_critical_event(event_name: NotificationEvents) -> bool:
        """
        Check if an event is critical (bypasses user preferences).
        
        Args:
            event_name: NotificationEvents enum value
            
        Returns:
            True if event is critical, False otherwise
        """
        event = NOTIFICATION_EVENTS.get(event_name)
        return event.bypasses_preferences if event else False
    
    @staticmethod
    def get_available_channels() -> List[NotificationChannel]:
        """
        Get list of currently available (implemented) channels.
        
        Returns:
            List of NotificationChannel enums that are implemented
        """
        available = []
        
        for channel in NotificationChannel:
            try:
                instance = NotificationManager._get_channel_instance(channel)
                if instance is not None:
                    available.append(channel)
            except ImportError:
                # Channel not available
                continue
        
        return available
    
    @staticmethod
    def send_with_channel_results(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> dict[str, bool]:
        """
        Send notification and return detailed results per channel.
        
        This method provides more detailed feedback about which channels
        succeeded or failed, useful for debugging and monitoring.
        
        Args:
            event_name: Notification event enum
            recipients: List of users to notify
            cluster: Cluster context
            context: Context data
            
        Returns:
            Dictionary mapping channel names to success status
        """
        # Input validation (same as main send method)
        if not isinstance(event_name, NotificationEvents):
            raise ValueError(f"event_name must be a NotificationEvents enum, got {type(event_name)}")
        
        if not isinstance(recipients, list):
            raise TypeError(f"recipients must be a list, got {type(recipients)}")
        
        if not isinstance(cluster, Cluster):
            raise TypeError(f"cluster must be a Cluster instance, got {type(cluster)}")
        
        if not isinstance(context, dict):
            raise TypeError(f"context must be a dictionary, got {type(context)}")
        
        # Get event definition
        event = NOTIFICATION_EVENTS.get(event_name)
        if not event:
            logger.error(f"Unknown event: {event_name}")
            return {}
        
        # Handle empty recipients list
        if not recipients:
            logger.info(f"No recipients provided for event: {event_name}")
            return {}
        
        # Validate cluster
        if not cluster or not hasattr(cluster, 'id'):
            logger.error(f"Invalid cluster provided for event: {event_name}")
            return {}
        
        # Send via supported channels
        channel_results = {}
        
        for channel in event.supported_channels:
            try:
                channel_success = NotificationManager._send_via_channel(
                    channel=channel,
                    event=event,
                    recipients=recipients,
                    cluster=cluster,
                    context=context
                )
                channel_results[channel.value] = channel_success
                
            except Exception as e:
                logger.error(
                    f"Unexpected error sending {event_name.value} via {channel.value}: {str(e)}"
                )
                channel_results[channel.value] = False
        
        return channel_results
    
    @staticmethod
    def _handle_critical_error(
        error: Exception,
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any]
    ) -> None:
        """
        Handle critical errors that occur during notification processing.
        
        This method provides centralized error handling for critical failures
        that prevent notification sending entirely.
        
        Args:
            error: The exception that occurred
            event_name: The notification event that failed
            recipients: The intended recipients
            cluster: The cluster context
            context: The notification context
        """
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'event_name': event_name.value if hasattr(event_name, 'value') else str(event_name),
            'recipient_count': len(recipients) if recipients else 0,
            'cluster_id': cluster.id if hasattr(cluster, 'id') else 'unknown',
            'cluster_name': cluster.name if hasattr(cluster, 'name') else 'unknown',
            'context_keys': list(context.keys()) if isinstance(context, dict) else 'invalid'
        }
        
        logger.critical(
            f"Critical notification failure: {error_details['error_type']} occurred "
            f"while sending {error_details['event_name']} to {error_details['recipient_count']} "
            f"recipients in cluster {error_details['cluster_name']} ({error_details['cluster_id']}). "
            f"Error: {error_details['error_message']}"
        )
        
        # Log additional context for debugging
        logger.debug(f"Critical error context: {error_details}")
    
    @staticmethod
    def _validate_notification_context(context: dict[str, Any], event_name: NotificationEvents) -> bool:
        """
        Validate that the notification context contains required data.
        
        This method performs basic validation of context data to catch
        common issues before attempting to send notifications.
        
        Args:
            context: The notification context to validate
            event_name: The event name for context-specific validation
            
        Returns:
            True if context is valid, False otherwise
        """
        try:
            # Basic validation - context should be a non-empty dict
            if not isinstance(context, dict):
                logger.error(f"Context must be a dictionary for {event_name.value}")
                return False
            
            # Check for potentially problematic values
            for key, value in context.items():
                if value is None:
                    logger.warning(f"Context key '{key}' is None for {event_name.value}")
                elif isinstance(value, str) and len(value.strip()) == 0:
                    logger.warning(f"Context key '{key}' is empty string for {event_name.value}")
            
            # Event-specific validation could be added here
            # For example, visitor events might require 'visitor_name'
            if event_name in [NotificationEvents.VISITOR_ARRIVAL, NotificationEvents.VISITOR_OVERSTAY]:
                if 'visitor_name' not in context:
                    logger.warning(f"Visitor event {event_name.value} missing 'visitor_name' in context")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating context for {event_name.value}: {str(e)}")
            return False