"""
Unit tests for NotificationManager.

This module tests the core functionality of the NotificationManager including
event validation, channel routing, error handling, and utility methods.
"""

import logging
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.notifications.manager import NotificationManager
from core.notifications.events import NotificationEvents, NotificationChannel, NotificationPriority
from core.common.models.cluster import Cluster

User = get_user_model()


class NotificationManagerTestCase(TestCase):
    """Test cases for NotificationManager functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test cluster
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street"
        )
        
        # Create test users
        self.user1 = User.objects.create_user(
            email_address="user1@test.com",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email_address="user2@test.com", 
            password="testpass123"
        )
        
        # Add users to cluster
        self.user1.clusters.add(self.cluster)
        self.user2.clusters.add(self.cluster)
        
        self.recipients = [self.user1, self.user2]
        self.context = {
            'visitor_name': 'John Doe',
            'unit': 'A101',
            'message': 'Test notification'
        }
    
    def test_send_valid_notification(self):
        """Test sending a valid notification with proper parameters."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = True
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertTrue(result)
            # Should be called once for EMAIL channel (VISITOR_ARRIVAL supports EMAIL)
            self.assertEqual(mock_send.call_count, 1)
    
    def test_send_invalid_event_name_type(self):
        """Test that invalid event_name type raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            NotificationManager.send(
                event_name="invalid_event",  # String instead of enum
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
        
        self.assertIn("event_name must be a NotificationEvents enum", str(cm.exception))
    
    def test_send_invalid_recipients_type(self):
        """Test that invalid recipients type raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients="invalid",  # String instead of list
                cluster=self.cluster,
                context=self.context
            )
        
        self.assertIn("recipients must be a list", str(cm.exception))
    
    def test_send_invalid_cluster_type(self):
        """Test that invalid cluster type raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster="invalid",  # String instead of Cluster
                context=self.context
            )
        
        self.assertIn("cluster must be a Cluster instance", str(cm.exception))
    
    def test_send_invalid_context_type(self):
        """Test that invalid context type raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context="invalid"  # String instead of dict
            )
        
        self.assertIn("context must be a dictionary", str(cm.exception))
    
    def test_send_empty_recipients_list(self):
        """Test that empty recipients list returns True without error."""
        result = NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[],
            cluster=self.cluster,
            context=self.context
        )
        
        self.assertTrue(result)
    
    def test_send_unknown_event(self):
        """Test handling of unknown event (should not happen with enum, but test registry lookup)."""
        # Mock the NOTIFICATION_EVENTS to return None
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.get.return_value = None
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
    
    def test_send_invalid_cluster_object(self):
        """Test handling of invalid cluster object."""
        # Create a mock object that's not a proper Cluster
        invalid_cluster = Mock()
        invalid_cluster.id = None
        
        result = NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=self.recipients,
            cluster=invalid_cluster,
            context=self.context
        )
        
        self.assertFalse(result)
    
    def test_send_multiple_channels_success(self):
        """Test sending notification with multiple channels all succeeding."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = True
            
            # Use emergency alert which supports multiple channels
            result = NotificationManager.send(
                event_name=NotificationEvents.EMERGENCY_ALERT,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertTrue(result)
            # EMERGENCY_ALERT supports EMAIL, SMS, WEBSOCKET, APP (4 channels)
            self.assertEqual(mock_send.call_count, 4)
    
    def test_send_multiple_channels_partial_failure(self):
        """Test sending notification with some channels failing."""
        def mock_send_side_effect(channel, event, recipients, cluster, context):
            # Fail SMS channel, succeed others
            return channel != NotificationChannel.SMS
        
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.side_effect = mock_send_side_effect
            
            result = NotificationManager.send(
                event_name=NotificationEvents.EMERGENCY_ALERT,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)  # Should fail if any channel fails
    
    def test_send_channel_exception_handling(self):
        """Test that exceptions in channel sending are handled gracefully."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.side_effect = Exception("Channel error")
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
    
    def test_get_event_info_valid_event(self):
        """Test getting event info for a valid event."""
        event_info = NotificationManager.get_event_info(NotificationEvents.VISITOR_ARRIVAL)
        
        self.assertIsNotNone(event_info)
        self.assertEqual(event_info.name, NotificationEvents.VISITOR_ARRIVAL.value)
        self.assertEqual(event_info.priority, NotificationPriority.HIGH)
    
    def test_get_event_info_invalid_event(self):
        """Test getting event info for an invalid event."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.get.return_value = None
            
            event_info = NotificationManager.get_event_info(NotificationEvents.VISITOR_ARRIVAL)
            self.assertIsNone(event_info)
    
    def test_validate_event_exists_valid(self):
        """Test validating that a valid event exists."""
        result = NotificationManager.validate_event_exists(NotificationEvents.VISITOR_ARRIVAL)
        self.assertTrue(result)
    
    def test_validate_event_exists_invalid(self):
        """Test validating that an invalid event doesn't exist."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.__contains__ = Mock(return_value=False)
            
            result = NotificationManager.validate_event_exists(NotificationEvents.VISITOR_ARRIVAL)
            self.assertFalse(result)
    
    def test_get_supported_channels_valid_event(self):
        """Test getting supported channels for a valid event."""
        channels = NotificationManager.get_supported_channels(NotificationEvents.VISITOR_ARRIVAL)
        
        self.assertIsInstance(channels, list)
        self.assertIn(NotificationChannel.EMAIL, channels)
    
    def test_get_supported_channels_invalid_event(self):
        """Test getting supported channels for an invalid event."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.get.return_value = None
            
            channels = NotificationManager.get_supported_channels(NotificationEvents.VISITOR_ARRIVAL)
            self.assertEqual(channels, [])
    
    def test_is_critical_event_true(self):
        """Test checking if a critical event is critical."""
        result = NotificationManager.is_critical_event(NotificationEvents.EMERGENCY_ALERT)
        self.assertTrue(result)
    
    def test_is_critical_event_false(self):
        """Test checking if a non-critical event is not critical."""
        result = NotificationManager.is_critical_event(NotificationEvents.VISITOR_ARRIVAL)
        self.assertFalse(result)
    
    def test_is_critical_event_invalid(self):
        """Test checking critical status for invalid event."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.get.return_value = None
            
            result = NotificationManager.is_critical_event(NotificationEvents.VISITOR_ARRIVAL)
            self.assertFalse(result)


class NotificationManagerChannelRoutingTestCase(TestCase):
    """Test cases for NotificationManager channel routing functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(name="Test Estate")
        self.user = User.objects.create_user(
            email_address="test@test.com",
            password="testpass123"
        )
        self.recipients = [self.user]
        self.context = {'test': 'data'}
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_email_success(self, mock_logger):
        """Test successful email channel routing."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        with patch('core.notifications.channels.email.EmailChannel') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_instance.send.return_value = True
            mock_email_class.return_value = mock_email_instance
            
            result = NotificationManager._send_via_channel(
                channel=NotificationChannel.EMAIL,
                event=mock_event,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertTrue(result)
            mock_email_instance.send.assert_called_once_with(
                mock_event, self.recipients, self.cluster, self.context
            )
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_email_failure(self, mock_logger):
        """Test email channel routing with send failure."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        with patch('core.notifications.channels.email.EmailChannel') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_instance.send.return_value = False
            mock_email_class.return_value = mock_email_instance
            
            result = NotificationManager._send_via_channel(
                channel=NotificationChannel.EMAIL,
                event=mock_event,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_import_error(self, mock_logger):
        """Test channel routing with import error."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = NotificationManager._send_via_channel(
                channel=NotificationChannel.EMAIL,
                event=mock_event,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_unimplemented_channels(self, mock_logger):
        """Test routing for unimplemented channels (SMS, WebSocket, App)."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        # Test SMS channel
        result = NotificationManager._send_via_channel(
            channel=NotificationChannel.SMS,
            event=mock_event,
            recipients=self.recipients,
            cluster=self.cluster,
            context=self.context
        )
        self.assertTrue(result)  # Should return True for unimplemented channels
        
        # Test WebSocket channel
        result = NotificationManager._send_via_channel(
            channel=NotificationChannel.WEBSOCKET,
            event=mock_event,
            recipients=self.recipients,
            cluster=self.cluster,
            context=self.context
        )
        self.assertTrue(result)
        
        # Test App channel
        result = NotificationManager._send_via_channel(
            channel=NotificationChannel.APP,
            event=mock_event,
            recipients=self.recipients,
            cluster=self.cluster,
            context=self.context
        )
        self.assertTrue(result)
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_unknown_channel(self, mock_logger):
        """Test routing for unknown channel."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        # Create a mock channel that's not in the enum
        unknown_channel = Mock()
        unknown_channel.value = "unknown"
        
        result = NotificationManager._send_via_channel(
            channel=unknown_channel,
            event=mock_event,
            recipients=self.recipients,
            cluster=self.cluster,
            context=self.context
        )
        
        self.assertFalse(result)
        mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_send_via_channel_exception_handling(self, mock_logger):
        """Test exception handling in channel routing."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        with patch('core.notifications.channels.email.EmailChannel') as mock_email_class:
            mock_email_class.side_effect = Exception("Unexpected error")
            
            result = NotificationManager._send_via_channel(
                channel=NotificationChannel.EMAIL,
                event=mock_event,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            mock_logger.error.assert_called()


class NotificationManagerChannelOrchestrationTestCase(TestCase):
    """Test cases for enhanced channel routing and orchestration logic."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(name="Test Estate")
        self.user = User.objects.create_user(
            email_address="test@test.com",
            password="testpass123"
        )
        self.recipients = [self.user]
        self.context = {'test': 'data'}
    
    def test_channel_results_aggregation(self):
        """Test that channel results are properly aggregated."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            # Mock different results for different channels
            def mock_send_side_effect(channel, event, recipients, cluster, context):
                if channel == NotificationChannel.EMAIL:
                    return True
                elif channel == NotificationChannel.SMS:
                    return False
                else:
                    return True
            
            mock_send.side_effect = mock_send_side_effect
            
            result = NotificationManager.send(
                event_name=NotificationEvents.EMERGENCY_ALERT,  # Supports multiple channels
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Should fail because SMS failed
            self.assertFalse(result)
    
    def test_send_with_channel_results_detailed_feedback(self):
        """Test detailed channel results method."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            # Mock different results for different channels
            def mock_send_side_effect(channel, event, recipients, cluster, context):
                return channel == NotificationChannel.EMAIL
            
            mock_send.side_effect = mock_send_side_effect
            
            results = NotificationManager.send_with_channel_results(
                event_name=NotificationEvents.EMERGENCY_ALERT,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that we get detailed results
            self.assertIsInstance(results, dict)
            self.assertIn('email', results)
            self.assertTrue(results['email'])
            
            # Other channels should be False (mocked to fail)
            for channel_name, success in results.items():
                if channel_name != 'email':
                    self.assertFalse(success)
    
    def test_get_channel_instance_email(self):
        """Test getting email channel instance."""
        with patch('core.notifications.channels.email.EmailChannel') as mock_email_class:
            mock_instance = Mock()
            mock_email_class.return_value = mock_instance
            
            instance = NotificationManager._get_channel_instance(NotificationChannel.EMAIL)
            
            self.assertEqual(instance, mock_instance)
            mock_email_class.assert_called_once()
    
    def test_get_channel_instance_unimplemented(self):
        """Test getting unimplemented channel instance."""
        instance = NotificationManager._get_channel_instance(NotificationChannel.SMS)
        self.assertIsNone(instance)
        
        instance = NotificationManager._get_channel_instance(NotificationChannel.WEBSOCKET)
        self.assertIsNone(instance)
        
        instance = NotificationManager._get_channel_instance(NotificationChannel.APP)
        self.assertIsNone(instance)
    
    def test_get_channel_instance_unknown(self):
        """Test getting unknown channel instance."""
        unknown_channel = Mock()
        unknown_channel.value = "unknown"
        
        with patch('core.notifications.manager.logger') as mock_logger:
            instance = NotificationManager._get_channel_instance(unknown_channel)
            
            self.assertIsNone(instance)
            mock_logger.error.assert_called()
    
    def test_get_available_channels(self):
        """Test getting list of available channels."""
        with patch('core.notifications.manager.NotificationManager._get_channel_instance') as mock_get:
            # Mock EMAIL as available, others as None
            def mock_get_side_effect(channel):
                return Mock() if channel == NotificationChannel.EMAIL else None
            
            mock_get.side_effect = mock_get_side_effect
            
            available = NotificationManager.get_available_channels()
            
            self.assertIn(NotificationChannel.EMAIL, available)
            self.assertNotIn(NotificationChannel.SMS, available)
            self.assertNotIn(NotificationChannel.WEBSOCKET, available)
            self.assertNotIn(NotificationChannel.APP, available)
    
    @patch('core.notifications.manager.logger')
    def test_channel_supports_event_validation(self, mock_logger):
        """Test that channel support for events is validated."""
        mock_event = Mock()
        mock_event.name = "test_event"
        
        with patch('core.notifications.manager.NotificationManager._get_channel_instance') as mock_get:
            mock_channel = Mock()
            mock_channel.supports_event.return_value = False  # Channel doesn't support event
            mock_get.return_value = mock_channel
            
            result = NotificationManager._send_via_channel(
                channel=NotificationChannel.EMAIL,
                event=mock_event,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            mock_logger.error.assert_called()
            mock_channel.supports_event.assert_called_once_with(mock_event)
    
    @patch('core.notifications.manager.logger')
    def test_enhanced_logging_for_channels(self, mock_logger):
        """Test enhanced logging for channel operations."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = True
            
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that debug and info logs were called
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()
    
    def test_partial_success_logging(self):
        """Test logging for partial success scenarios."""
        with patch('core.notifications.manager.logger') as mock_logger:
            with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
                # Mock partial success - some channels succeed, others fail
                def mock_send_side_effect(channel, event, recipients, cluster, context):
                    return channel == NotificationChannel.EMAIL
                
                mock_send.side_effect = mock_send_side_effect
                
                result = NotificationManager.send(
                    event_name=NotificationEvents.EMERGENCY_ALERT,  # Multiple channels
                    recipients=self.recipients,
                    cluster=self.cluster,
                    context=self.context
                )
                
                self.assertFalse(result)  # Overall failure due to some channels failing
                
                # Check that warning was logged for partial success
                mock_logger.warning.assert_called()
    
    def test_all_channels_failure_logging(self):
        """Test logging when all channels fail."""
        with patch('core.notifications.manager.logger') as mock_logger:
            with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
                mock_send.return_value = False  # All channels fail
                
                result = NotificationManager.send(
                    event_name=NotificationEvents.VISITOR_ARRIVAL,
                    recipients=self.recipients,
                    cluster=self.cluster,
                    context=self.context
                )
                
                self.assertFalse(result)
                
                # Check that error was logged for all channels failing
                mock_logger.error.assert_called()


class NotificationManagerErrorHandlingTestCase(TestCase):
    """Test cases for comprehensive error handling and logging."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(name="Test Estate")
        self.user = User.objects.create_user(
            email_address="test@test.com",
            password="testpass123"
        )
        self.recipients = [self.user]
        self.context = {'test': 'data'}
    
    @patch('core.notifications.manager.logger')
    def test_enhanced_parameter_validation_logging(self, mock_logger):
        """Test enhanced parameter validation with detailed logging."""
        # Test invalid event_name
        with self.assertRaises(ValueError):
            NotificationManager.send(
                event_name="invalid",
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
        mock_logger.error.assert_called()
        
        # Test invalid recipients
        with self.assertRaises(TypeError):
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients="invalid",
                cluster=self.cluster,
                context=self.context
            )
        mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_recipient_validation_error_handling(self, mock_logger):
        """Test validation of recipient objects."""
        # Create invalid recipient (missing required attributes)
        invalid_recipient = Mock()
        del invalid_recipient.email_address  # Remove required attribute
        
        result = NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[invalid_recipient],
            cluster=self.cluster,
            context=self.context
        )
        
        self.assertFalse(result)
        mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_cluster_validation_error_handling(self, mock_logger):
        """Test cluster validation with detailed error messages."""
        # Test cluster without ID
        invalid_cluster = Mock()
        invalid_cluster.id = None
        
        result = NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=self.recipients,
            cluster=invalid_cluster,
            context=self.context
        )
        
        self.assertFalse(result)
        mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_channel_specific_error_handling(self, mock_logger):
        """Test handling of different types of channel errors."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            # Test ValueError in channel
            mock_send.side_effect = ValueError("Channel validation error")
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_import_error_handling(self, mock_logger):
        """Test handling of ImportError for channel implementations."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.side_effect = ImportError("Channel module not found")
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_no_supported_channels_handling(self, mock_logger):
        """Test handling when event has no supported channels."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_event = Mock()
            mock_event.supported_channels = []  # No channels
            mock_events.get.return_value = mock_event
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertTrue(result)  # Should succeed with warning
            mock_logger.warning.assert_called()
    
    def test_handle_critical_error_method(self):
        """Test the critical error handling method."""
        test_error = ValueError("Test critical error")
        
        with patch('core.notifications.manager.logger') as mock_logger:
            NotificationManager._handle_critical_error(
                error=test_error,
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            mock_logger.critical.assert_called()
            mock_logger.debug.assert_called()
    
    def test_validate_notification_context_valid(self):
        """Test context validation with valid context."""
        valid_context = {
            'visitor_name': 'John Doe',
            'unit': 'A101',
            'message': 'Test message'
        }
        
        result = NotificationManager._validate_notification_context(
            valid_context, 
            NotificationEvents.VISITOR_ARRIVAL
        )
        
        self.assertTrue(result)
    
    @patch('core.notifications.manager.logger')
    def test_validate_notification_context_invalid(self, mock_logger):
        """Test context validation with invalid context."""
        # Test non-dict context
        result = NotificationManager._validate_notification_context(
            "invalid_context", 
            NotificationEvents.VISITOR_ARRIVAL
        )
        
        self.assertFalse(result)
        mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_validate_notification_context_warnings(self, mock_logger):
        """Test context validation warnings for problematic values."""
        problematic_context = {
            'visitor_name': None,  # None value
            'unit': '',  # Empty string
            'message': 'Valid message'
        }
        
        result = NotificationManager._validate_notification_context(
            problematic_context, 
            NotificationEvents.VISITOR_ARRIVAL
        )
        
        self.assertTrue(result)  # Should still be valid but with warnings
        mock_logger.warning.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_validate_notification_context_visitor_specific(self, mock_logger):
        """Test visitor-specific context validation."""
        context_without_visitor_name = {
            'unit': 'A101',
            'message': 'Test message'
        }
        
        result = NotificationManager._validate_notification_context(
            context_without_visitor_name, 
            NotificationEvents.VISITOR_ARRIVAL
        )
        
        self.assertTrue(result)  # Should be valid but with warning
        mock_logger.warning.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_detailed_error_logging_in_final_results(self, mock_logger):
        """Test detailed error logging in final results."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.side_effect = ValueError("Test channel error")
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            self.assertFalse(result)
            
            # Check that detailed error information was logged
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if 'Error in' in str(call)]
            self.assertTrue(len(error_calls) > 0)
    
    @patch('core.notifications.manager.logger')
    def test_context_validation_integration(self, mock_logger):
        """Test that context validation is integrated into main send method."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = True
            
            # Use context that will trigger warnings
            problematic_context = {'visitor_name': None}
            
            result = NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=problematic_context
            )
            
            self.assertTrue(result)
            # Should have warning about context validation issues
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'Context validation issues' in str(call)]
            self.assertTrue(len(warning_calls) > 0)


class NotificationManagerLoggingTestCase(TestCase):
    """Test cases for NotificationManager logging functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(name="Test Estate")
        self.user = User.objects.create_user(
            email_address="test@test.com",
            password="testpass123"
        )
        self.recipients = [self.user]
        self.context = {'test': 'data'}
    
    @patch('core.notifications.manager.logger')
    def test_logging_successful_notification(self, mock_logger):
        """Test logging for successful notification."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = True
            
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that info logs were called
            mock_logger.info.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_logging_failed_notification(self, mock_logger):
        """Test logging for failed notification."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.return_value = False
            
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that warning log was called
            mock_logger.warning.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_logging_exception_in_channel(self, mock_logger):
        """Test logging when exception occurs in channel."""
        with patch('core.notifications.manager.NotificationManager._send_via_channel') as mock_send:
            mock_send.side_effect = Exception("Test exception")
            
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that error log was called
            mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_logging_empty_recipients(self, mock_logger):
        """Test logging for empty recipients list."""
        NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[],
            cluster=self.cluster,
            context=self.context
        )
        
        # Check that info log was called for empty recipients
        mock_logger.info.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_logging_unknown_event(self, mock_logger):
        """Test logging for unknown event."""
        with patch('core.notifications.manager.NOTIFICATION_EVENTS') as mock_events:
            mock_events.get.return_value = None
            
            NotificationManager.send(
                event_name=NotificationEvents.VISITOR_ARRIVAL,
                recipients=self.recipients,
                cluster=self.cluster,
                context=self.context
            )
            
            # Check that error log was called
            mock_logger.error.assert_called()
    
    @patch('core.notifications.manager.logger')
    def test_logging_invalid_cluster(self, mock_logger):
        """Test logging for invalid cluster."""
        invalid_cluster = Mock()
        invalid_cluster.id = None
        
        NotificationManager.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=self.recipients,
            cluster=invalid_cluster,
            context=self.context
        )
        
        # Check that error log was called
        mock_logger.error.assert_called()