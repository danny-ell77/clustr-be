"""
Unit tests for EmailChannel implementation.

This module contains comprehensive tests for the EmailChannel class,
covering initialization, basic structure, and core functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from django.test import TestCase
from django.template import Context

from core.notifications.channels.email import EmailChannel
from core.notifications.events import NotificationEvent, NotificationEvents, NotificationPriority
from core.common.email_sender import NotificationTypes
from accounts.models.user_settings import UserSettings
from accounts.models import AccountUser
from core.common.models.cluster import Cluster


class TestEmailChannelStructure(TestCase):
    """Test EmailChannel class structure and initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.email_channel = EmailChannel()
        
        # Create test cluster
        self.cluster = Mock(spec=Cluster)
        self.cluster.name = "Test Estate"
        
        # Create test users
        self.user1 = Mock(spec=AccountUser)
        self.user1.id = 1
        self.user1.email_address = "user1@example.com"
        self.user1.name = "User One"
        
        self.user2 = Mock(spec=AccountUser)
        self.user2.id = 2
        self.user2.email_address = "user2@example.com"
        self.user2.name = "User Two"
        
        # Create test event
        self.test_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
    
    def test_email_channel_initialization(self):
        """Test EmailChannel can be initialized properly."""
        channel = EmailChannel()
        self.assertIsInstance(channel, EmailChannel)
        self.assertEqual(channel.get_channel_name(), "EMAIL")
    
    def test_event_email_type_mapping_exists(self):
        """Test that EVENT_EMAIL_TYPE_MAPPING dictionary is properly defined."""
        self.assertTrue(hasattr(EmailChannel, 'EVENT_EMAIL_TYPE_MAPPING'))
        self.assertIsInstance(EmailChannel.EVENT_EMAIL_TYPE_MAPPING, dict)
        
        # Check that critical events are mapped
        self.assertIn(NotificationEvents.EMERGENCY_ALERT.value, EmailChannel.EVENT_EMAIL_TYPE_MAPPING)
        self.assertEqual(
            EmailChannel.EVENT_EMAIL_TYPE_MAPPING[NotificationEvents.EMERGENCY_ALERT.value],
            NotificationTypes.EMERGENCY_ALERT
        )
        
        # Check that visitor events are mapped
        self.assertIn(NotificationEvents.VISITOR_ARRIVAL.value, EmailChannel.EVENT_EMAIL_TYPE_MAPPING)
        self.assertEqual(
            EmailChannel.EVENT_EMAIL_TYPE_MAPPING[NotificationEvents.VISITOR_ARRIVAL.value],
            NotificationTypes.VISITOR_ARRIVAL
        )
        
        # Check that payment events are mapped
        self.assertIn(NotificationEvents.PAYMENT_DUE.value, EmailChannel.EVENT_EMAIL_TYPE_MAPPING)
        self.assertEqual(
            EmailChannel.EVENT_EMAIL_TYPE_MAPPING[NotificationEvents.PAYMENT_DUE.value],
            NotificationTypes.BILL_REMINDER
        )
    
    def test_get_channel_name(self):
        """Test get_channel_name returns correct channel name."""
        self.assertEqual(self.email_channel.get_channel_name(), "EMAIL")
    
    def test_validate_recipients_with_valid_emails(self):
        """Test validate_recipients with users having valid email addresses."""
        recipients = [self.user1, self.user2]
        valid_recipients = self.email_channel.validate_recipients(recipients)
        
        self.assertEqual(len(valid_recipients), 2)
        self.assertIn(self.user1, valid_recipients)
        self.assertIn(self.user2, valid_recipients)
    
    def test_validate_recipients_with_invalid_emails(self):
        """Test validate_recipients filters out users with invalid email addresses."""
        # Create user with invalid email
        invalid_user = Mock(spec=AccountUser)
        invalid_user.id = 3
        invalid_user.email_address = "invalid-email"
        invalid_user.name = "Invalid User"
        
        # Create user with no email
        no_email_user = Mock(spec=AccountUser)
        no_email_user.id = 4
        no_email_user.email_address = None
        no_email_user.name = "No Email User"
        
        recipients = [self.user1, invalid_user, no_email_user]
        valid_recipients = self.email_channel.validate_recipients(recipients)
        
        self.assertEqual(len(valid_recipients), 1)
        self.assertIn(self.user1, valid_recipients)
        self.assertNotIn(invalid_user, valid_recipients)
        self.assertNotIn(no_email_user, valid_recipients)
    
    def test_validate_recipients_with_empty_list(self):
        """Test validate_recipients with empty recipient list."""
        valid_recipients = self.email_channel.validate_recipients([])
        self.assertEqual(len(valid_recipients), 0)
    
    def test_transform_context_basic_functionality(self):
        """Test transform_context adds basic email formatting."""
        base_context = {
            'message': 'Test message',
            'cluster': self.cluster,
            'user': self.user1
        }
        
        transformed = self.email_channel.transform_context(base_context, self.test_event)
        
        # Should preserve original context
        self.assertEqual(transformed['message'], 'Test message')
        
        # Should add common email formatting
        self.assertIn('current_time', transformed)
        self.assertIn('cluster_name', transformed)
        self.assertIn('user_name', transformed)
        self.assertEqual(transformed['cluster_name'], 'Test Estate')
        self.assertEqual(transformed['user_name'], 'User One')
    
    def test_transform_context_visitor_arrival(self):
        """Test transform_context for visitor arrival events."""
        arrival_time = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        base_context = {
            'visitor_name': 'John Doe',
            'arrival_time': arrival_time,
            'access_code': 'ABC123'
        }
        
        visitor_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, visitor_event)
        
        self.assertEqual(transformed['visitor_name'], 'John Doe')
        self.assertEqual(transformed['access_code'], 'ABC123')
        self.assertIn('formatted_arrival_time', transformed)
        self.assertEqual(transformed['formatted_arrival_time'], '14:30 on January 15, 2024')
    
    def test_transform_context_payment_due(self):
        """Test transform_context for payment due events."""
        due_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        base_context = {
            'amount': 150.50,
            'due_date': due_date,
            'bill_number': 'BILL-001'
        }
        
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        with patch('core.notifications.channels.email.datetime') as mock_datetime:
            # Mock current time to be before due date
            mock_now = datetime(2024, 1, 25, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            transformed = self.email_channel.transform_context(base_context, payment_event)
        
        self.assertEqual(transformed['amount'], 150.50)
        self.assertEqual(transformed['bill_number'], 'BILL-001')
        self.assertIn('formatted_amount', transformed)
        self.assertEqual(transformed['formatted_amount'], '$150.50')
        self.assertIn('formatted_due_date', transformed)
        self.assertEqual(transformed['formatted_due_date'], 'February 01, 2024')
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_by_preferences_critical_event(self, mock_get_or_create):
        """Test that critical events bypass user preferences."""
        # Create critical event
        critical_event = NotificationEvent(
            name=NotificationEvents.EMERGENCY_ALERT.value,
            priority=NotificationPriority.CRITICAL,
            supported_channels=[]
        )
        
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, critical_event, self.cluster
        )
        
        # Should return all recipients without checking preferences
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
        
        # Should not have called get_or_create since preferences are bypassed
        mock_get_or_create.assert_not_called()
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_by_preferences_non_critical_event(self, mock_get_or_create):
        """Test that non-critical events respect user preferences."""
        # Mock user settings
        mock_settings1 = Mock()
        mock_settings1.get_notification_preference.return_value = True
        
        mock_settings2 = Mock()
        mock_settings2.get_notification_preference.return_value = False
        
        mock_get_or_create.side_effect = [
            (mock_settings1, False),  # user1 settings
            (mock_settings2, False),  # user2 settings
        ]
        
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.test_event, self.cluster
        )
        
        # Should return only user1 (who has notifications enabled)
        self.assertEqual(len(filtered), 1)
        self.assertIn(self.user1, filtered)
        self.assertNotIn(self.user2, filtered)
        
        # Should have checked preferences for both users
        mock_settings1.get_notification_preference.assert_called_once_with(
            NotificationEvents.VISITOR_ARRIVAL.value, 'EMAIL'
        )
        mock_settings2.get_notification_preference.assert_called_once_with(
            NotificationEvents.VISITOR_ARRIVAL.value, 'EMAIL'
        )


class TestEmailChannelContextTransformation(TestCase):
    """Test context transformation methods in detail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.email_channel = EmailChannel()
    
    def test_transform_visitor_context_with_times(self):
        """Test visitor context transformation with arrival and departure times."""
        context = {
            'arrival_time': datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
            'departure_time': datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc),
            'visitor_name': 'Jane Doe'
        }
        
        self.email_channel._transform_visitor_context(context)
        
        self.assertEqual(context['formatted_arrival_time'], '14:30 on January 15, 2024')
        self.assertEqual(context['formatted_departure_time'], '18:45 on January 15, 2024')
        self.assertEqual(context['visitor_name'], 'Jane Doe')  # Should be unchanged
    
    def test_transform_visitor_context_with_invalid_times(self):
        """Test visitor context transformation handles invalid datetime objects."""
        context = {
            'arrival_time': 'invalid-datetime',
            'departure_time': None,
            'visitor_name': 'Jane Doe'
        }
        
        # Should not raise exception
        self.email_channel._transform_visitor_context(context)
        
        # Should not add formatted times for invalid values
        self.assertNotIn('formatted_arrival_time', context)
        self.assertNotIn('formatted_departure_time', context)
    
    def test_transform_payment_context_with_valid_data(self):
        """Test payment context transformation with valid data."""
        due_date = datetime(2024, 2, 15, tzinfo=timezone.utc)
        context = {
            'amount': 250.75,
            'due_date': due_date,
            'bill_number': 'BILL-002'
        }
        
        with patch('core.notifications.channels.email.datetime') as mock_datetime:
            # Mock current time to be 5 days before due date
            mock_now = datetime(2024, 2, 10, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            self.email_channel._transform_payment_context(context)
        
        self.assertEqual(context['formatted_amount'], '$250.75')
        self.assertEqual(context['formatted_due_date'], 'February 15, 2024')
        self.assertEqual(context['days_until_due'], 5)
        self.assertNotIn('days_overdue', context)
    
    def test_transform_payment_context_overdue(self):
        """Test payment context transformation for overdue payments."""
        due_date = datetime(2024, 2, 10, tzinfo=timezone.utc)
        context = {
            'amount': 100.00,
            'due_date': due_date
        }
        
        with patch('core.notifications.channels.email.datetime') as mock_datetime:
            # Mock current time to be 3 days after due date
            mock_now = datetime(2024, 2, 13, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            self.email_channel._transform_payment_context(context)
        
        self.assertEqual(context['formatted_amount'], '$100.00')
        self.assertEqual(context['days_overdue'], 3)
        self.assertNotIn('days_until_due', context)
    
    def test_transform_payment_receipt_context(self):
        """Test payment receipt context transformation."""
        payment_date = datetime(2024, 1, 20, 15, 30, tzinfo=timezone.utc)
        context = {
            'payment_amount': 150.00,
            'remaining_amount': 0.00,
            'payment_date': payment_date,
            'transaction_id': 'TXN-12345'
        }
        
        self.email_channel._transform_payment_receipt_context(context)
        
        self.assertEqual(context['formatted_payment_amount'], '$150.00')
        self.assertEqual(context['formatted_remaining_amount'], '$0.00')
        self.assertEqual(context['formatted_payment_date'], 'January 20, 2024 at 15:30')
        self.assertEqual(context['transaction_id'], 'TXN-12345')  # Should be unchanged
    
    def test_transform_emergency_context(self):
        """Test emergency context transformation."""
        alert_time = datetime(2024, 1, 15, 10, 45, tzinfo=timezone.utc)
        context = {
            'alert_time': alert_time,
            'severity': 'high',
            'message': 'Fire alarm activated'
        }
        
        self.email_channel._transform_emergency_context(context)
        
        self.assertEqual(context['formatted_alert_time'], '10:45 on January 15, 2024')
        self.assertEqual(context['severity'], 'HIGH')  # Should be uppercase
        self.assertEqual(context['message'], 'Fire alarm activated')  # Should be unchanged
    
    def test_add_common_email_formatting(self):
        """Test common email formatting additions."""
        cluster_mock = Mock()
        cluster_mock.name = "Test Estate"
        
        user_mock = Mock()
        user_mock.name = "Test User"
        
        context = {
            'cluster': cluster_mock,
            'user': user_mock,
            'existing_field': 'existing_value'
        }
        
        self.email_channel._add_common_email_formatting(context)
        
        # Should add current time
        self.assertIn('current_time', context)
        
        # Should add cluster name
        self.assertIn('cluster_name', context)
        self.assertEqual(context['cluster_name'], 'Test Estate')
        
        # Should add user name
        self.assertIn('user_name', context)
        self.assertEqual(context['user_name'], 'Test User')
        
        # Should preserve existing fields
        self.assertEqual(context['existing_field'], 'existing_value')
    
    def test_add_common_email_formatting_with_missing_objects(self):
        """Test common email formatting handles missing cluster/user objects."""
        context = {
            'cluster': None,
            'user': None,
            'existing_field': 'existing_value'
        }
        
        # Should not raise exception
        self.email_channel._add_common_email_formatting(context)
        
        # Should still add current time
        self.assertIn('current_time', context)
        
        # Should not add cluster_name or user_name for None objects
        self.assertNotIn('cluster_name', context)
        self.assertNotIn('user_name', context)
        
        # Should preserve existing fields
        self.assertEqual(context['existing_field'], 'existing_value')

class Te
stEmailChannelPreferenceFiltering(TestCase):
    """Test email preference filtering functionality in detail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.email_channel = EmailChannel()
        
        # Create test cluster
        self.cluster = Mock(spec=Cluster)
        self.cluster.name = "Test Estate"
        
        # Create test users
        self.user1 = Mock(spec=AccountUser)
        self.user1.id = 1
        self.user1.email_address = "user1@example.com"
        self.user1.name = "User One"
        
        self.user2 = Mock(spec=AccountUser)
        self.user2.id = 2
        self.user2.email_address = "user2@example.com"
        self.user2.name = "User Two"
        
        self.user3 = Mock(spec=AccountUser)
        self.user3.id = 3
        self.user3.email_address = "user3@example.com"
        self.user3.name = "User Three"
        
        # Create test events
        self.critical_event = NotificationEvent(
            name=NotificationEvents.EMERGENCY_ALERT.value,
            priority=NotificationPriority.CRITICAL,
            supported_channels=[]
        )
        
        self.non_critical_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_all_enabled(self, mock_get_or_create):
        """Test filtering when all users have notifications enabled."""
        # Mock all users having notifications enabled
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = True
        
        mock_get_or_create.return_value = (mock_settings, False)
        
        recipients = [self.user1, self.user2, self.user3]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should return all recipients
        self.assertEqual(len(filtered), 3)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
        self.assertIn(self.user3, filtered)
        
        # Should have checked preferences for all users
        self.assertEqual(mock_get_or_create.call_count, 3)
        self.assertEqual(mock_settings.get_notification_preference.call_count, 3)
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_all_disabled(self, mock_get_or_create):
        """Test filtering when all users have notifications disabled."""
        # Mock all users having notifications disabled
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = False
        
        mock_get_or_create.return_value = (mock_settings, False)
        
        recipients = [self.user1, self.user2, self.user3]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should return no recipients
        self.assertEqual(len(filtered), 0)
        
        # Should have checked preferences for all users
        self.assertEqual(mock_get_or_create.call_count, 3)
        self.assertEqual(mock_settings.get_notification_preference.call_count, 3)
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_mixed_preferences(self, mock_get_or_create):
        """Test filtering with mixed user preferences."""
        # Mock different preferences for different users
        def mock_get_or_create_side_effect(user):
            mock_settings = Mock()
            if user == self.user1:
                mock_settings.get_notification_preference.return_value = True
            elif user == self.user2:
                mock_settings.get_notification_preference.return_value = False
            else:  # user3
                mock_settings.get_notification_preference.return_value = True
            return (mock_settings, False)
        
        mock_get_or_create.side_effect = mock_get_or_create_side_effect
        
        recipients = [self.user1, self.user2, self.user3]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should return only users with notifications enabled (user1 and user3)
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.user1, filtered)
        self.assertNotIn(self.user2, filtered)
        self.assertIn(self.user3, filtered)
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_critical_event_bypasses_preferences(self, mock_get_or_create):
        """Test that critical events bypass user preferences completely."""
        # Mock all users having notifications disabled
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = False
        
        mock_get_or_create.return_value = (mock_settings, False)
        
        recipients = [self.user1, self.user2, self.user3]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.critical_event, self.cluster
        )
        
        # Should return all recipients despite disabled preferences
        self.assertEqual(len(filtered), 3)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
        self.assertIn(self.user3, filtered)
        
        # Should not have checked preferences at all
        mock_get_or_create.assert_not_called()
        mock_settings.get_notification_preference.assert_not_called()
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_handles_settings_creation(self, mock_get_or_create):
        """Test that filtering handles UserSettings creation for new users."""
        # Mock settings being created (not just retrieved)
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = True
        
        # Return True for created flag to simulate new settings
        mock_get_or_create.return_value = (mock_settings, True)
        
        recipients = [self.user1]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should work correctly even when settings are created
        self.assertEqual(len(filtered), 1)
        self.assertIn(self.user1, filtered)
        
        # Should have called get_or_create
        mock_get_or_create.assert_called_once_with(user=self.user1)
        mock_settings.get_notification_preference.assert_called_once_with(
            NotificationEvents.VISITOR_ARRIVAL.value, 'EMAIL'
        )
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    @patch('core.notifications.channels.email.logger')
    def test_filter_recipients_handles_exceptions(self, mock_logger, mock_get_or_create):
        """Test that filtering handles exceptions gracefully."""
        # Mock exception during settings lookup
        mock_get_or_create.side_effect = Exception("Database error")
        
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should include all users when exceptions occur (fail-safe behavior)
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
        
        # Should have logged errors
        self.assertEqual(mock_logger.error.call_count, 2)
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_with_empty_list(self, mock_get_or_create):
        """Test filtering with empty recipient list."""
        filtered = self.email_channel.filter_recipients_by_preferences(
            [], self.non_critical_event, self.cluster
        )
        
        # Should return empty list
        self.assertEqual(len(filtered), 0)
        
        # Should not have called get_or_create
        mock_get_or_create.assert_not_called()
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_uses_correct_event_name(self, mock_get_or_create):
        """Test that filtering uses the correct event name for preference lookup."""
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = True
        
        mock_get_or_create.return_value = (mock_settings, False)
        
        # Test with different event types
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        recipients = [self.user1]
        self.email_channel.filter_recipients_by_preferences(
            recipients, payment_event, self.cluster
        )
        
        # Should have used the correct event name
        mock_settings.get_notification_preference.assert_called_once_with(
            NotificationEvents.PAYMENT_DUE.value, 'EMAIL'
        )
    
    @patch('core.notifications.channels.email.UserSettings.objects.get_or_create')
    def test_filter_recipients_uses_email_channel(self, mock_get_or_create):
        """Test that filtering always uses EMAIL channel for preference lookup."""
        mock_settings = Mock()
        mock_settings.get_notification_preference.return_value = True
        
        mock_get_or_create.return_value = (mock_settings, False)
        
        recipients = [self.user1]
        self.email_channel.filter_recipients_by_preferences(
            recipients, self.non_critical_event, self.cluster
        )
        
        # Should have used EMAIL channel
        mock_settings.get_notification_preference.assert_called_once_with(
            NotificationEvents.VISITOR_ARRIVAL.value, 'EMAIL'
        )


class TestEmailChannelPreferenceIntegration(TestCase):
    """Test email preference filtering with real UserSettings model."""
    
    def setUp(self):
        """Set up test fixtures with real models."""
        from django.contrib.auth import get_user_model
        from core.common.models.cluster import Cluster
        
        User = get_user_model()
        
        # Create real test cluster
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test St"
        )
        
        # Create real test users
        self.user1 = User.objects.create_user(
            email_address="user1@example.com",
            name="User One",
            cluster=self.cluster
        )
        
        self.user2 = User.objects.create_user(
            email_address="user2@example.com", 
            name="User Two",
            cluster=self.cluster
        )
        
        self.email_channel = EmailChannel()
        
        self.test_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
    
    def test_filter_recipients_with_real_settings_default_enabled(self):
        """Test filtering with real UserSettings using default preferences."""
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.test_event, self.cluster
        )
        
        # By default, email notifications should be enabled
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
    
    def test_filter_recipients_with_disabled_preferences(self):
        """Test filtering when user explicitly disables email notifications."""
        # Disable email notifications for user1
        settings1, _ = UserSettings.objects.get_or_create(user=self.user1)
        settings1.set_notification_preference(
            NotificationEvents.VISITOR_ARRIVAL.value, 'EMAIL', False
        )
        
        # Keep user2 with default settings (enabled)
        
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, self.test_event, self.cluster
        )
        
        # Should only include user2
        self.assertEqual(len(filtered), 1)
        self.assertNotIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)
    
    def test_filter_recipients_critical_event_with_disabled_preferences(self):
        """Test that critical events bypass disabled preferences."""
        # Disable email notifications for both users
        settings1, _ = UserSettings.objects.get_or_create(user=self.user1)
        settings1.set_notification_preference(
            NotificationEvents.EMERGENCY_ALERT.value, 'EMAIL', False
        )
        
        settings2, _ = UserSettings.objects.get_or_create(user=self.user2)
        settings2.set_notification_preference(
            NotificationEvents.EMERGENCY_ALERT.value, 'EMAIL', False
        )
        
        critical_event = NotificationEvent(
            name=NotificationEvents.EMERGENCY_ALERT.value,
            priority=NotificationPriority.CRITICAL,
            supported_channels=[]
        )
        
        recipients = [self.user1, self.user2]
        filtered = self.email_channel.filter_recipients_by_preferences(
            recipients, critical_event, self.cluster
        )
        
        # Should include both users despite disabled preferences
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.user1, filtered)
        self.assertIn(self.user2, filtered)

class 
TestEmailChannelContextTransformationComprehensive(TestCase):
    """Comprehensive tests for context transformation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.email_channel = EmailChannel()
        
        # Create mock cluster and user for common formatting tests
        self.cluster_mock = Mock()
        self.cluster_mock.name = "Test Estate"
        
        self.user_mock = Mock()
        self.user_mock.name = "Test User"
    
    def test_transform_context_visitor_arrival_complete(self):
        """Test complete visitor arrival context transformation."""
        arrival_time = datetime(2024, 3, 15, 9, 30, tzinfo=timezone.utc)
        base_context = {
            'visitor_name': 'John Smith',
            'arrival_time': arrival_time,
            'access_code': 'XYZ789',
            'unit': 'A-101',
            'host_name': 'Jane Doe',
            'cluster': self.cluster_mock,
            'user': self.user_mock
        }
        
        visitor_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, visitor_event)
        
        # Should preserve original context
        self.assertEqual(transformed['visitor_name'], 'John Smith')
        self.assertEqual(transformed['access_code'], 'XYZ789')
        self.assertEqual(transformed['unit'], 'A-101')
        self.assertEqual(transformed['host_name'], 'Jane Doe')
        
        # Should add formatted arrival time
        self.assertIn('formatted_arrival_time', transformed)
        self.assertEqual(transformed['formatted_arrival_time'], '09:30 on March 15, 2024')
        
        # Should add common email formatting
        self.assertIn('current_time', transformed)
        self.assertIn('cluster_name', transformed)
        self.assertIn('user_name', transformed)
        self.assertEqual(transformed['cluster_name'], 'Test Estate')
        self.assertEqual(transformed['user_name'], 'Test User')
    
    def test_transform_context_visitor_overstay_complete(self):
        """Test complete visitor overstay context transformation."""
        arrival_time = datetime(2024, 3, 15, 9, 30, tzinfo=timezone.utc)
        departure_time = datetime(2024, 3, 15, 17, 45, tzinfo=timezone.utc)
        
        base_context = {
            'visitor_name': 'Bob Johnson',
            'arrival_time': arrival_time,
            'departure_time': departure_time,
            'access_code': 'ABC456',
            'overstay_duration': '2 hours',
            'cluster': self.cluster_mock
        }
        
        overstay_event = NotificationEvent(
            name=NotificationEvents.VISITOR_OVERSTAY.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, overstay_event)
        
        # Should preserve original context
        self.assertEqual(transformed['visitor_name'], 'Bob Johnson')
        self.assertEqual(transformed['access_code'], 'ABC456')
        self.assertEqual(transformed['overstay_duration'], '2 hours')
        
        # Should add formatted times
        self.assertIn('formatted_arrival_time', transformed)
        self.assertIn('formatted_departure_time', transformed)
        self.assertEqual(transformed['formatted_arrival_time'], '09:30 on March 15, 2024')
        self.assertEqual(transformed['formatted_departure_time'], '17:45 on March 15, 2024')
    
    def test_transform_context_payment_due_with_future_date(self):
        """Test payment due context transformation with future due date."""
        due_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        base_context = {
            'amount': 275.50,
            'due_date': due_date,
            'bill_number': 'BILL-2024-001',
            'bill_title': 'Monthly Maintenance Fee',
            'bill_type': 'Maintenance',
            'user': self.user_mock
        }
        
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        with patch('core.notifications.channels.email.datetime') as mock_datetime:
            # Mock current time to be 10 days before due date
            mock_now = datetime(2024, 3, 22, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            transformed = self.email_channel.transform_context(base_context, payment_event)
        
        # Should preserve original context
        self.assertEqual(transformed['amount'], 275.50)
        self.assertEqual(transformed['bill_number'], 'BILL-2024-001')
        self.assertEqual(transformed['bill_title'], 'Monthly Maintenance Fee')
        self.assertEqual(transformed['bill_type'], 'Maintenance')
        
        # Should add formatted amount and date
        self.assertIn('formatted_amount', transformed)
        self.assertIn('formatted_due_date', transformed)
        self.assertEqual(transformed['formatted_amount'], '$275.50')
        self.assertEqual(transformed['formatted_due_date'], 'April 01, 2024')
        
        # Should calculate days until due
        self.assertIn('days_until_due', transformed)
        self.assertEqual(transformed['days_until_due'], 10)
        self.assertNotIn('days_overdue', transformed)
    
    def test_transform_context_payment_overdue(self):
        """Test payment context transformation for overdue payments."""
        due_date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        base_context = {
            'amount': 150.00,
            'due_date': due_date,
            'bill_number': 'BILL-2024-002',
            'penalty_amount': 15.00
        }
        
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_OVERDUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        with patch('core.notifications.channels.email.datetime') as mock_datetime:
            # Mock current time to be 7 days after due date
            mock_now = datetime(2024, 3, 22, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            transformed = self.email_channel.transform_context(base_context, payment_event)
        
        # Should add overdue information
        self.assertIn('days_overdue', transformed)
        self.assertEqual(transformed['days_overdue'], 7)
        self.assertNotIn('days_until_due', transformed)
        
        # Should format amounts
        self.assertEqual(transformed['formatted_amount'], '$150.00')
    
    def test_transform_context_payment_confirmed_complete(self):
        """Test complete payment confirmation context transformation."""
        payment_date = datetime(2024, 3, 20, 14, 25, tzinfo=timezone.utc)
        base_context = {
            'payment_amount': 200.00,
            'remaining_amount': 50.00,
            'payment_date': payment_date,
            'transaction_id': 'TXN-789012',
            'bill_number': 'BILL-2024-003',
            'bill_title': 'Utility Bill',
            'payment_method': 'Credit Card',
            'bill_status': 'Partially Paid'
        }
        
        payment_confirmed_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_CONFIRMED.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, payment_confirmed_event)
        
        # Should preserve original context
        self.assertEqual(transformed['transaction_id'], 'TXN-789012')
        self.assertEqual(transformed['bill_number'], 'BILL-2024-003')
        self.assertEqual(transformed['bill_title'], 'Utility Bill')
        self.assertEqual(transformed['payment_method'], 'Credit Card')
        self.assertEqual(transformed['bill_status'], 'Partially Paid')
        
        # Should add formatted amounts and date
        self.assertIn('formatted_payment_amount', transformed)
        self.assertIn('formatted_remaining_amount', transformed)
        self.assertIn('formatted_payment_date', transformed)
        self.assertEqual(transformed['formatted_payment_amount'], '$200.00')
        self.assertEqual(transformed['formatted_remaining_amount'], '$50.00')
        self.assertEqual(transformed['formatted_payment_date'], 'March 20, 2024 at 14:25')
    
    def test_transform_context_emergency_alert_complete(self):
        """Test complete emergency alert context transformation."""
        alert_time = datetime(2024, 3, 20, 11, 15, tzinfo=timezone.utc)
        base_context = {
            'alert_time': alert_time,
            'severity': 'critical',
            'alert_message': 'Fire alarm activated in Building A',
            'location': 'Building A - 3rd Floor',
            'emergency_contact': '911',
            'evacuation_point': 'Main Parking Lot',
            'cluster': self.cluster_mock
        }
        
        emergency_event = NotificationEvent(
            name=NotificationEvents.EMERGENCY_ALERT.value,
            priority=NotificationPriority.CRITICAL,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, emergency_event)
        
        # Should preserve original context
        self.assertEqual(transformed['alert_message'], 'Fire alarm activated in Building A')
        self.assertEqual(transformed['location'], 'Building A - 3rd Floor')
        self.assertEqual(transformed['emergency_contact'], '911')
        self.assertEqual(transformed['evacuation_point'], 'Main Parking Lot')
        
        # Should add formatted alert time
        self.assertIn('formatted_alert_time', transformed)
        self.assertEqual(transformed['formatted_alert_time'], '11:15 on March 20, 2024')
        
        # Should convert severity to uppercase
        self.assertIn('severity', transformed)
        self.assertEqual(transformed['severity'], 'CRITICAL')
    
    def test_transform_context_announcement_posted(self):
        """Test announcement posted context transformation."""
        base_context = {
            'announcement_title': 'Pool Maintenance Schedule',
            'announcement_content': 'The pool will be closed for maintenance...',
            'author_name': 'Estate Manager',
            'posted_date': datetime(2024, 3, 20, tzinfo=timezone.utc),
            'category': 'Maintenance',
            'cluster': self.cluster_mock,
            'user': self.user_mock
        }
        
        announcement_event = NotificationEvent(
            name=NotificationEvents.ANNOUNCEMENT_POSTED.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, announcement_event)
        
        # Should preserve all original context
        self.assertEqual(transformed['announcement_title'], 'Pool Maintenance Schedule')
        self.assertEqual(transformed['announcement_content'], 'The pool will be closed for maintenance...')
        self.assertEqual(transformed['author_name'], 'Estate Manager')
        self.assertEqual(transformed['category'], 'Maintenance')
        
        # Should add common email formatting
        self.assertIn('current_time', transformed)
        self.assertIn('cluster_name', transformed)
        self.assertIn('user_name', transformed)
    
    def test_transform_context_handles_missing_fields(self):
        """Test context transformation handles missing fields gracefully."""
        # Test with minimal context
        base_context = {
            'message': 'Basic message'
        }
        
        visitor_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
        
        # Should not raise exception
        transformed = self.email_channel.transform_context(base_context, visitor_event)
        
        # Should preserve existing fields
        self.assertEqual(transformed['message'], 'Basic message')
        
        # Should add current_time even without cluster/user
        self.assertIn('current_time', transformed)
        
        # Should not add formatted times for missing fields
        self.assertNotIn('formatted_arrival_time', transformed)
    
    def test_transform_context_handles_invalid_data_types(self):
        """Test context transformation handles invalid data types gracefully."""
        base_context = {
            'amount': 'invalid-amount',  # Should be numeric
            'due_date': 'invalid-date',  # Should be datetime
            'arrival_time': None,  # Should be datetime
            'severity': None,  # Should be string
            'cluster': 'invalid-cluster',  # Should be object with name attribute
            'user': None  # Should be object with name attribute
        }
        
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        # Should not raise exception
        transformed = self.email_channel.transform_context(base_context, payment_event)
        
        # Should preserve original invalid values
        self.assertEqual(transformed['amount'], 'invalid-amount')
        self.assertEqual(transformed['due_date'], 'invalid-date')
        self.assertEqual(transformed['arrival_time'], None)
        
        # Should not add formatted versions for invalid data
        self.assertNotIn('formatted_amount', transformed)
        self.assertNotIn('formatted_due_date', transformed)
        self.assertNotIn('formatted_arrival_time', transformed)
        
        # Should still add current_time
        self.assertIn('current_time', transformed)
    
    def test_transform_context_preserves_existing_formatted_fields(self):
        """Test that transformation doesn't overwrite existing formatted fields."""
        base_context = {
            'amount': 100.00,
            'formatted_amount': '$100.00 (Custom Format)',  # Pre-existing formatted field
            'cluster': self.cluster_mock
        }
        
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        transformed = self.email_channel.transform_context(base_context, payment_event)
        
        # Should preserve existing formatted field (not overwrite)
        self.assertEqual(transformed['formatted_amount'], '$100.00 (Custom Format)')
    
    def test_transform_context_different_event_types_isolation(self):
        """Test that different event types don't interfere with each other."""
        base_context = {
            'amount': 100.00,
            'arrival_time': datetime(2024, 3, 20, tzinfo=timezone.utc),
            'severity': 'high'
        }
        
        # Test with payment event - should only transform payment fields
        payment_event = NotificationEvent(
            name=NotificationEvents.PAYMENT_DUE.value,
            priority=NotificationPriority.MEDIUM,
            supported_channels=[]
        )
        
        payment_transformed = self.email_channel.transform_context(base_context, payment_event)
        
        # Should transform payment fields
        self.assertIn('formatted_amount', payment_transformed)
        # Should not transform visitor fields
        self.assertNotIn('formatted_arrival_time', payment_transformed)
        # Should not transform emergency fields (severity should remain lowercase)
        self.assertEqual(payment_transformed['severity'], 'high')
        
        # Test with visitor event - should only transform visitor fields
        visitor_event = NotificationEvent(
            name=NotificationEvents.VISITOR_ARRIVAL.value,
            priority=NotificationPriority.HIGH,
            supported_channels=[]
        )
        
        visitor_transformed = self.email_channel.transform_context(base_context, visitor_event)
        
        # Should transform visitor fields
        self.assertIn('formatted_arrival_time', visitor_transformed)
        # Should not transform payment fields
        self.assertNotIn('formatted_amount', visitor_transformed)
        # Should not transform emergency fields
        self.assertEqual(visitor_transformed['severity'], 'high')
    
    def test_common_email_formatting_comprehensive(self):
        """Test comprehensive common email formatting functionality."""
        cluster_mock = Mock()
        cluster_mock.name = "Premium Estate Complex"
        
        user_mock = Mock()
        user_mock.name = "John Alexander Smith"
        
        base_context = {
            'cluster': cluster_mock,
            'user': user_mock,
            'existing_cluster_name': 'Should not be overwritten',
            'existing_user_name': 'Should not be overwritten'
        }
        
        self.email_channel._add_common_email_formatting(base_context)
        
        # Should add current time
        self.assertIn('current_time', base_context)
        self.assertIsInstance(base_context['current_time'], str)
        self.assertIn('UTC', base_context['current_time'])
        
        # Should add cluster name from object
        self.assertIn('cluster_name', base_context)
        self.assertEqual(base_context['cluster_name'], 'Premium Estate Complex')
        
        # Should add user name from object
        self.assertIn('user_name', base_context)
        self.assertEqual(base_context['user_name'], 'John Alexander Smith')
        
        # Should not overwrite existing fields
        self.assertEqual(base_context['existing_cluster_name'], 'Should not be overwritten')
        self.assertEqual(base_context['existing_user_name'], 'Should not be overwritten')