"""
NotificationManager - Central orchestrator for the ClustR notification system.

This module provides the main API for sending notifications across different channels
with proper event validation, channel routing, and error handling.
"""

import typing
import logging
import concurrent.futures
from typing import List, Any, Optional

from django.contrib.auth import get_user_model

from core.notifications.events import (
    NotificationEvents,
    NotificationEvent,
    NOTIFICATION_EVENTS,
    NotificationChannel,
)
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
    """

    @staticmethod
    def send(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """Send notification asynchronously via Celery task."""
        if not NotificationManager._validate_inputs(event_name, recipients, cluster, context):
            return False

        event = NOTIFICATION_EVENTS.get(event_name)
        if not event:
            logger.error(f"Unknown event: {event_name}")
            return False

        # Critical events are sent synchronously
        if event.bypasses_preferences:
            logger.info(f"Critical event {event_name.value} - sending synchronously")
            return NotificationManager.send_sync(event_name, recipients, cluster, context)

        return NotificationManager._dispatch_task(
            'send_notification_task', event_name, recipients, cluster, context
        )

    @staticmethod
    def send_sync(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """Send notification synchronously (immediately)."""
        if not NotificationManager._validate_inputs(event_name, recipients, cluster, context):
            return False

        try:
            return NotificationManager._send_notification_internal(
                event_name, recipients, cluster, context
            )
        except Exception as e:
            logger.error(f"Error in synchronous notification sending for event {event_name.value}: {str(e)}")
            return False

    @staticmethod
    def send_with_retry(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
        max_retries: int = 3,
    ) -> bool:
        """Send notification with retry logic via Celery task."""
        if not NotificationManager._validate_inputs(event_name, recipients, cluster, context):
            return False

        return NotificationManager._dispatch_task(
            'send_notification_with_retry_task', event_name, recipients, cluster, context, max_retries
        )

    @staticmethod
    def _validate_inputs(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """Validate all inputs for notification sending."""
        try:
            # Type validation
            assert isinstance(event_name, NotificationEvents), \
                f"event_name must be a NotificationEvents enum, got {type(event_name).__name__}"
            assert isinstance(recipients, list), \
                f"recipients must be a list, got {type(recipients).__name__}"
            assert isinstance(cluster, Cluster), \
                f"cluster must be a Cluster instance, got {type(cluster).__name__}"
            assert isinstance(context, dict), \
                f"context must be a dictionary, got {type(context).__name__}"

            # Event exists
            if event_name not in NOTIFICATION_EVENTS:
                logger.error(f"Unknown event: {event_name}. Available: {list(NOTIFICATION_EVENTS.keys())}")
                return False

            # Empty recipients handling
            if not recipients:
                logger.info(f"No recipients provided for event: {event_name.value}")
                return True

            # Validate recipients
            invalid_recipients = [
                f"index {i}: {type(recipient).__name__}"
                for i, recipient in enumerate(recipients)
                if not (hasattr(recipient, "email_address") and hasattr(recipient, "id"))
            ]
            if invalid_recipients:
                logger.error(f"Invalid recipients for {event_name.value}: {', '.join(invalid_recipients)}")
                return False

            # Validate cluster
            if not (cluster and hasattr(cluster, "id") and cluster.id):
                logger.error(f"Invalid cluster for {event_name.value}: cluster must have a valid ID")
                return False

            event = NOTIFICATION_EVENTS[event_name]
            logger.info(
                f"Sending {event_name.value} notification to {len(recipients)} recipients "
                f"in cluster {getattr(cluster, 'name', cluster.id)} (priority: {event.priority_level})"
            )
            return True

        except Exception as e:
            logger.error(f"Input validation failed for {event_name.value}: {str(e)}")
            return False

    @staticmethod
    def _dispatch_task(task_name: str, event_name: NotificationEvents, recipients: List["User"], 
                      cluster: Cluster, context: dict[str, Any], max_retries: int = None) -> bool:
        """Dispatch Celery task for notification sending."""
        try:
            # Prepare serializable data
            task_data = {
                'event_name': event_name.value,
                'recipient_ids': [str(user.id) for user in recipients],
                'cluster_id': str(cluster.id),
                'context': context,
            }
            if max_retries is not None:
                task_data['max_retries'] = max_retries

            # Import and dispatch task
            from core.common.tasks.notification import send_notification_task, send_notification_with_retry_task
            
            task_func = send_notification_task if task_name == 'send_notification_task' else send_notification_with_retry_task
            task_result = task_func.delay(**task_data)

            logger.info(
                f"Notification task dispatched for event {event_name.value}: "
                f"{len(recipients)} recipients, cluster {getattr(cluster, 'name', cluster.id)}, "
                f"task_id: {task_result.id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error dispatching {task_name} for event {event_name.value}: {str(e)}")
            return False

    @staticmethod
    def _send_notification_internal(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """Internal method that performs the actual notification sending."""
        event = NOTIFICATION_EVENTS.get(event_name)
        if not event:
            logger.error(f"Unknown event: {event_name}")
            return False

        if not event.supported_channels:
            logger.warning(f"Event {event_name.value} has no supported channels configured")
            return True

        # Send via all supported channels concurrently
        channel_results = {}
        channel_errors = {}

        def send_channel(channel):
            """Helper function to send via a single channel."""
            channel_name = channel.value
            try:
                logger.debug(f"Sending {event_name.value} via {channel_name} to {len(recipients)} recipients")
                
                success = NotificationManager._send_via_channel(channel, event, recipients, cluster, context)
                
                log_level = logger.debug if success else logger.warning
                status = "Successfully sent" if success else "Failed to send"
                log_level(f"{status} {event_name.value} via {channel_name}")
                
                return channel_name, success, None

            except (ValueError, ImportError) as e:
                error_msg = f"{type(e).__name__} in {channel_name} channel: {str(e)}"
                logger.error(error_msg)
                return channel_name, False, error_msg
            except Exception as e:
                error_msg = f"Unexpected error in {channel_name} channel: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                return channel_name, False, error_msg

        # Execute channel sending concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(event.supported_channels)) as executor:
            future_to_channel = {
                executor.submit(send_channel, channel): channel 
                for channel in event.supported_channels
            }
            
            for future in concurrent.futures.as_completed(future_to_channel):
                channel_name, success, error = future.result()
                channel_results[channel_name] = success
                if error:
                    channel_errors[channel_name] = error

        return NotificationManager._log_results_and_return_status(
            event_name, recipients, channel_results, channel_errors
        )

    @staticmethod
    def _log_results_and_return_status(
        event_name: NotificationEvents,
        recipients: List["User"],
        channel_results: dict[str, bool],
        channel_errors: dict[str, str]
    ) -> bool:
        """Log final results and return overall success status."""
        successful_channels = [ch for ch, success in channel_results.items() if success]
        failed_channels = [ch for ch, success in channel_results.items() if not success]
        overall_success = len(failed_channels) == 0

        recipient_count = len(recipients)
        base_msg = f"{event_name.value} notification to {recipient_count} recipients"

        if overall_success:
            logger.info(f"Successfully sent {base_msg} via all {len(successful_channels)} channels: {', '.join(successful_channels)}")
        elif successful_channels:
            logger.warning(
                f"Partial success for {base_msg}. "
                f"Successful ({len(successful_channels)}): {', '.join(successful_channels)}. "
                f"Failed ({len(failed_channels)}): {', '.join(failed_channels)}"
            )
            # Log specific errors
            for channel_name in failed_channels:
                if channel_name in channel_errors:
                    logger.error(f"Error in {channel_name}: {channel_errors[channel_name]}")
        else:
            logger.error(f"All {len(failed_channels)} channels failed for {base_msg}")
            for channel_name, error_msg in channel_errors.items():
                logger.error(f"Error in {channel_name}: {error_msg}")

        return overall_success

    @staticmethod
    def _send_via_channel(
        channel: NotificationChannel,
        event: NotificationEvent,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> bool:
        """Send notification via a specific channel."""
        channel_instance = NotificationManager._get_channel_instance(channel)
        
        if channel_instance is None:
            logger.warning(f"{channel.value.upper()} channel not yet implemented for event: {event.name}")
            return True  # Don't fail overall notification for unimplemented channels

        if not channel_instance.supports_event(event):
            logger.error(f"{channel.value.upper()} channel does not support event: {event.name}")
            return False

        logger.debug(f"Sending {event.name} to {len(recipients)} recipients via {channel.value.upper()}")
        return channel_instance.send(event, recipients, cluster, context)

    @staticmethod
    def _get_channel_instance(channel: NotificationChannel):
        """Get an instance of the specified channel."""
        channel_map = {
            NotificationChannel.EMAIL: ('core.notifications.channels.email', 'EmailChannel'),
            NotificationChannel.SMS: ('core.notifications.channels.sms', 'SMSChannel'),
            NotificationChannel.WEBSOCKET: ('core.notifications.channels.websocket', 'WebSocketChannel'),
            NotificationChannel.APP: ('core.notifications.channels.app', 'AppChannel'),
        }

        if channel not in channel_map:
            logger.error(f"Unknown channel: {channel}")
            return None

        module_path, class_name = channel_map[channel]
        
        try:
            from importlib import import_module
            module = import_module(module_path)
            return getattr(module, class_name)()
        except ImportError:
            # Future implementation - return None for unimplemented channels
            return None

    # Utility methods
    @staticmethod
    def get_event_info(event_name: NotificationEvents) -> Optional[NotificationEvent]:
        """Get information about a specific notification event."""
        return NOTIFICATION_EVENTS.get(event_name)

    @staticmethod
    def validate_event_exists(event_name: NotificationEvents) -> bool:
        """Validate that an event exists in the registry."""
        return event_name in NOTIFICATION_EVENTS

    @staticmethod
    def get_supported_channels(event_name: NotificationEvents) -> List[NotificationChannel]:
        """Get the list of channels that support a specific event."""
        event = NOTIFICATION_EVENTS.get(event_name)
        return event.supported_channels if event else []

    @staticmethod
    def is_critical_event(event_name: NotificationEvents) -> bool:
        """Check if an event is critical (bypasses user preferences)."""
        event = NOTIFICATION_EVENTS.get(event_name)
        return event.bypasses_preferences if event else False

    @staticmethod
    def get_available_channels() -> List[NotificationChannel]:
        """Get list of currently available (implemented) channels."""
        return [
            channel for channel in NotificationChannel
            if NotificationManager._get_channel_instance(channel) is not None
        ]

    @staticmethod
    def send_with_channel_results(
        event_name: NotificationEvents,
        recipients: List["User"],
        cluster: Cluster,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        """Send notification and return detailed results per channel."""
        if not NotificationManager._validate_inputs(event_name, recipients, cluster, context):
            return {}

        event = NOTIFICATION_EVENTS.get(event_name)
        if not event or not recipients:
            return {}

        return {
            channel.value: NotificationManager._send_via_channel(channel, event, recipients, cluster, context)
            for channel in event.supported_channels
        }