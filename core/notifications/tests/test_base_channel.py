"""
Unit tests for base notification channel interface.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.notifications.channels.base import BaseNotificationChannel
from core.notifications.events import (
    NotificationEvent, 
    NotificationPriority, 
    NotificationChannel,
    NotificationEvents
)

User = get_user_model()


class ConcreteNotificationChannel(BaseNotificationChannel):
    """Concrete implementation for testing purposes."""
    
    def send(self, event, recipients, cluster, context):
        return True
    
    def filter_recipients_by_preferences(self, recipients, event, cluster):
        return recipients
    
    def transform_context(self, base_context, event):
        return base_context.copy()
    
    def validate_recipients(self, recipients):
        return recipients
    
    def get_channel_name(self):
        return "TEST"


class TestBaseNotificationChannel(TestCase):
    """Test BaseNotificationChannel abstract class functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.channel = ConcreteNotificationChannel()
        
        self.event = NotificationEvent(
            name="test_event",
            priority=NotificationPriority.MEDIUM,
            supported_channels=[NotificationChannel.EMAIL]
        )
        
        self.cluster = Mock()
        self.cluster.id = "test-cluster-id"
        
        self.user = Mock()
        self.user.email_address = "test@example.com"
        self.user.id = "test-user-id"
        
        self.context = {"message": "Test message"}
    
    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""
        base_channel = BaseNotificationChannel()
        
        with self.assertRaises(NotImplementedError):
            base_channel.send(self.event, [self.user], self.cluster, self.context)
        
        with self.assertRaises(NotImplementedError):
            base_channel.filter_recipients_by_preferences([self.user], self.event, self.cluster)
        
        with self.assertRaises(NotImplementedError):
            base_channel.transform_context(self.context, self.event)
        
        with self.assertRaises(NotImplementedError):
            base_channel.validate_recipients([self.user])
        
        with self.assertRaises(NotImplementedError):
            base_channel.get_channel_name()
    
    @patch('core.notifications.channels.base.NotificationLog')
    def test_log_notification_attempt_success(self, mock_notification_log):
        """Test logging successful notification attempt."""
        self.channel.log_notification_attempt(
            event=self.event,
            recipient=self.user,
            cluster=self.cluster,
            success=True,
            context=self.context
        )
        
        mock_notification_log.objects.create.assert_called_once_with(
            cluster=self.cluster,
            event=self.event.name,
            recipient=self.user,
            channel="TEST",
            success=True,
            error_message=None,
            context_data=self.context
        )
    
    @patch('core.notifications.channels.base.NotificationLog')
    def test_log_notification_attempt_failure(self, mock_notification_log):
        """Test logging failed notification attempt."""
        error_message = "SMTP connection failed"
        
        self.channel.log_notification_attempt(
            event=self.event,
            recipient=self.user,
            cluster=self.cluster,
            success=False,
            context=self.context,
            error_message=error_message
        )
        
        mock_notification_log.objects.create.assert_called_once_with(
            cluster=self.cluster,
            event=self.event.name,
            recipient=self.user,
            channel="TEST",
            success=False,
            error_message=error_message,
            context_data=self.context
        )
    
    def test_supports_event_true(self):
        """Test supports_event returns True for supported events."""
        # Create event that supports EMAIL channel
        email_event = NotificationEvent(
            name="email_event",
            priority=NotificationPriority.MEDIUM,
            supported_channels=[NotificationChannel.EMAIL]
        )
        
        # Create email channel
        email_channel = ConcreteNotificationChannel()
        email_channel.get_channel_name = Mock(return_value="EMAIL")
        
        self.assertTrue(email_channel.supports_event(email_event))
    
    def test_supports_event_false(self):
        """Test supports_event returns False for unsupported events."""
        # Create event that only supports SMS
        sms_event = NotificationEvent(
            name="sms_event",
            priority=NotificationPriority.HIGH,
            supported_channels=[NotificationChannel.SMS]
        )
        
        # Create email channel
        email_channel = ConcreteNotificationChannel()
        email_channel.get_channel_name = Mock(return_value="EMAIL")
        
        self.assertFalse(email_channel.supports_event(sms_event))
    
    def test_supports_event_invalid_channel(self):
        """Test supports_event returns False for invalid channel names."""
        invalid_channel = ConcreteNotificationChannel()
        invalid_channel.get_channel_name = Mock(return_value="INVALID")
        
        self.assertFalse(invalid_channel.supports_event(self.event))
    
    def test_get_preference_key(self):
        """Test get_preference_key generates correct preference key."""
        preference_key = self.channel.get_preference_key(self.event)
        expected = f"{self.event.name}_test"
        self.assertEqual(preference_key, expected)
    
    @patch('core.notifications.channels.base.logging.getLogger')
    def test_handle_send_error(self, mock_get_logger):
        """Test handle_send_error logs and records error properly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Mock the log_notification_attempt method
        self.channel.log_notification_attempt = Mock()
        
        # Create a test exception
        test_error = ValueError("Test error message")
        
        # Call handle_send_error
        self.channel.handle_send_error(
            error=test_error,
            event=self.event,
            recipient=self.user,
            cluster=self.cluster,
            context=self.context
        )
        
        # Verify logger was called
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("ValueError: Test error message", error_call_args)
        self.assertIn(self.event.name, error_call_args)
        self.assertIn(self.user.email_address, error_call_args)
        self.assertIn("TEST", error_call_args)
        
        # Verify log_notification_attempt was called
        self.channel.log_notification_attempt.assert_called_once_with(
            event=self.event,
            recipient=self.user,
            cluster=self.cluster,
            success=False,
            context=self.context,
            error_message="ValueError: Test error message"
        )
    
    def test_concrete_implementation_works(self):
        """Test that concrete implementation can be instantiated and used."""
        # Test that all abstract methods are implemented
        result = self.channel.send(self.event, [self.user], self.cluster, self.context)
        self.assertTrue(result)
        
        filtered = self.channel.filter_recipients_by_preferences([self.user], self.event, self.cluster)
        self.assertEqual(filtered, [self.user])
        
        transformed = self.channel.transform_context(self.context, self.event)
        self.assertEqual(transformed, self.context)
        
        validated = self.channel.validate_recipients([self.user])
        self.assertEqual(validated, [self.user])
        
        channel_name = self.channel.get_channel_name()
        self.assertEqual(channel_name, "TEST")


class TestChannelInterfaceDocumentation(unittest.TestCase):
    """Test that the interface is well-documented and provides usage examples."""
    
    def test_base_class_has_docstring(self):
        """Test that BaseNotificationChannel has comprehensive docstring."""
        docstring = BaseNotificationChannel.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("Abstract base class", docstring)
        self.assertIn("notification channels", docstring)
        self.assertIn("preference filtering", docstring)
        self.assertIn("context transformation", docstring)
    
    def test_send_method_has_docstring(self):
        """Test that send method has comprehensive docstring."""
        docstring = BaseNotificationChannel.send.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("Send notification", docstring)
        self.assertIn("Args:", docstring)
        self.assertIn("Returns:", docstring)
        self.assertIn("Raises:", docstring)
    
    def test_filter_recipients_method_has_docstring(self):
        """Test that filter_recipients_by_preferences has docstring."""
        docstring = BaseNotificationChannel.filter_recipients_by_preferences.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("Filter recipients", docstring)
        self.assertIn("preferences", docstring)
        self.assertIn("critical events", docstring)
    
    def test_transform_context_method_has_docstring(self):
        """Test that transform_context has docstring."""
        docstring = BaseNotificationChannel.transform_context.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("Transform base context", docstring)
        self.assertIn("channel-specific", docstring)
        self.assertIn("formatting", docstring)


if __name__ == '__main__':
    unittest.main()