"""
Unit tests for notification models.
"""

import unittest
from unittest.mock import Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from core.notifications.models import NotificationLog
from core.common.models.cluster import Cluster

User = get_user_model()


class TestNotificationLog(TestCase):
    """Test NotificationLog model functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test cluster
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street"
        )
        
        # Create a test user
        self.user = User.objects.create_user(
            email_address="test@example.com",
            password="testpass123"
        )
        
        # Create test notification log
        self.notification_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="visitor_arrival",
            recipient=self.user,
            channel="EMAIL",
            success=True,
            context_data={"visitor_name": "John Doe", "unit": "A101"}
        )
    
    def test_notification_log_creation(self):
        """Test that notification log is created correctly."""
        self.assertEqual(self.notification_log.cluster, self.cluster)
        self.assertEqual(self.notification_log.event, "visitor_arrival")
        self.assertEqual(self.notification_log.recipient, self.user)
        self.assertEqual(self.notification_log.channel, "EMAIL")
        self.assertTrue(self.notification_log.success)
        self.assertEqual(self.notification_log.context_data["visitor_name"], "John Doe")
    
    def test_notification_log_str_representation(self):
        """Test string representation of notification log."""
        expected = f"✓ visitor_arrival → {self.user.email_address} via EMAIL"
        self.assertEqual(str(self.notification_log), expected)
    
    def test_notification_log_str_representation_failed(self):
        """Test string representation for failed notification."""
        failed_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="payment_due",
            recipient=self.user,
            channel="EMAIL",
            success=False,
            error_message="SMTP connection failed"
        )
        
        expected = f"✗ payment_due → {self.user.email_address} via EMAIL"
        self.assertEqual(str(failed_log), expected)
    
    def test_is_successful_property(self):
        """Test is_successful property."""
        self.assertTrue(self.notification_log.is_successful)
        
        failed_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="payment_due",
            recipient=self.user,
            channel="EMAIL",
            success=False
        )
        self.assertFalse(failed_log.is_successful)
    
    def test_has_error_property(self):
        """Test has_error property."""
        # Successful notification should not have error
        self.assertFalse(self.notification_log.has_error)
        
        # Failed notification without error message
        failed_log_no_error = NotificationLog.objects.create(
            cluster=self.cluster,
            event="payment_due",
            recipient=self.user,
            channel="EMAIL",
            success=False
        )
        self.assertFalse(failed_log_no_error.has_error)
        
        # Failed notification with error message
        failed_log_with_error = NotificationLog.objects.create(
            cluster=self.cluster,
            event="payment_due",
            recipient=self.user,
            channel="EMAIL",
            success=False,
            error_message="SMTP connection failed"
        )
        self.assertTrue(failed_log_with_error.has_error)
    
    def test_get_context_summary_with_data(self):
        """Test get_context_summary with context data."""
        summary = self.notification_log.get_context_summary()
        self.assertIn("Context:", summary)
        self.assertIn("visitor_name", summary)
        self.assertIn("unit", summary)
    
    def test_get_context_summary_empty(self):
        """Test get_context_summary with empty context."""
        empty_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="system_update",
            recipient=self.user,
            channel="EMAIL",
            success=True,
            context_data={}
        )
        
        summary = empty_log.get_context_summary()
        self.assertEqual(summary, "No context data")
    
    def test_get_context_summary_many_keys(self):
        """Test get_context_summary with many context keys."""
        large_context = {
            "key1": "value1",
            "key2": "value2", 
            "key3": "value3",
            "key4": "value4",
            "key5": "value5"
        }
        
        large_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="announcement_posted",
            recipient=self.user,
            channel="EMAIL",
            success=True,
            context_data=large_context
        )
        
        summary = large_log.get_context_summary()
        self.assertIn("Context:", summary)
        self.assertIn("... and 2 more", summary)
    
    def test_default_values(self):
        """Test default values for model fields."""
        minimal_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="test_event",
            recipient=self.user
        )
        
        self.assertEqual(minimal_log.channel, "EMAIL")
        self.assertFalse(minimal_log.success)
        self.assertEqual(minimal_log.context_data, {})
        self.assertIsNone(minimal_log.error_message)
    
    def test_model_ordering(self):
        """Test that logs are ordered by sent_at descending."""
        # Create another log
        second_log = NotificationLog.objects.create(
            cluster=self.cluster,
            event="payment_due",
            recipient=self.user,
            channel="EMAIL",
            success=True
        )
        
        # Get all logs
        logs = list(NotificationLog.objects.all())
        
        # Second log should come first (more recent)
        self.assertEqual(logs[0], second_log)
        self.assertEqual(logs[1], self.notification_log)
    
    def test_cluster_relationship(self):
        """Test cluster foreign key relationship."""
        self.assertEqual(self.notification_log.cluster, self.cluster)
        
        # Test related name
        cluster_logs = self.cluster.notification_logs.all()
        self.assertIn(self.notification_log, cluster_logs)
    
    def test_recipient_relationship(self):
        """Test recipient foreign key relationship."""
        self.assertEqual(self.notification_log.recipient, self.user)
        
        # Test related name
        user_notifications = self.user.received_notifications.all()
        self.assertIn(self.notification_log, user_notifications)
    
    def test_cascade_deletion_cluster(self):
        """Test that logs are deleted when cluster is deleted."""
        log_id = self.notification_log.id
        self.cluster.delete()
        
        with self.assertRaises(NotificationLog.DoesNotExist):
            NotificationLog.objects.get(id=log_id)
    
    def test_cascade_deletion_user(self):
        """Test that logs are deleted when user is deleted."""
        log_id = self.notification_log.id
        self.user.delete()
        
        with self.assertRaises(NotificationLog.DoesNotExist):
            NotificationLog.objects.get(id=log_id)


if __name__ == '__main__':
    unittest.main()