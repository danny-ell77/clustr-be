"""
Unit tests for notification events, priorities, and channels.
"""

import unittest
from core.notifications.events import (
    NotificationPriority,
    NotificationChannel,
    NotificationEvents,
    NotificationEvent,
    NOTIFICATION_EVENTS,
    get_event,
    get_events_by_priority,
    get_critical_events
)


class TestNotificationPriority(unittest.TestCase):
    """Test NotificationPriority enum functionality."""
    
    def test_priority_values(self):
        """Test that priority values are correct integers."""
        self.assertEqual(NotificationPriority.CRITICAL, 1)
        self.assertEqual(NotificationPriority.HIGH, 2)
        self.assertEqual(NotificationPriority.MEDIUM, 3)
        self.assertEqual(NotificationPriority.LOW, 4)
    
    def test_priority_ordering(self):
        """Test that priorities can be compared correctly."""
        self.assertTrue(NotificationPriority.CRITICAL < NotificationPriority.HIGH)
        self.assertTrue(NotificationPriority.HIGH < NotificationPriority.MEDIUM)
        self.assertTrue(NotificationPriority.MEDIUM < NotificationPriority.LOW)


class TestNotificationChannel(unittest.TestCase):
    """Test NotificationChannel enum functionality."""
    
    def test_channel_values(self):
        """Test that channel values are correct strings."""
        self.assertEqual(NotificationChannel.EMAIL.value, "email")
        self.assertEqual(NotificationChannel.SMS.value, "sms")
        self.assertEqual(NotificationChannel.WEBSOCKET.value, "websocket")
        self.assertEqual(NotificationChannel.APP.value, "app")


class TestNotificationEvent(unittest.TestCase):
    """Test NotificationEvent class functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.critical_event = NotificationEvent(
            name="test_critical",
            priority=NotificationPriority.CRITICAL,
            supported_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS]
        )
        
        self.medium_event = NotificationEvent(
            name="test_medium",
            priority=NotificationPriority.MEDIUM,
            supported_channels=[NotificationChannel.EMAIL]
        )
    
    def test_bypasses_preferences_critical(self):
        """Test that critical events bypass preferences."""
        self.assertTrue(self.critical_event.bypasses_preferences)
    
    def test_bypasses_preferences_non_critical(self):
        """Test that non-critical events don't bypass preferences."""
        self.assertFalse(self.medium_event.bypasses_preferences)
    
    def test_priority_level_property(self):
        """Test priority_level property returns correct string."""
        self.assertEqual(self.critical_event.priority_level, "CRITICAL")
        self.assertEqual(self.medium_event.priority_level, "MEDIUM")
    
    def test_supports_channel_true(self):
        """Test supports_channel returns True for supported channels."""
        self.assertTrue(self.critical_event.supports_channel(NotificationChannel.EMAIL))
        self.assertTrue(self.critical_event.supports_channel(NotificationChannel.SMS))
    
    def test_supports_channel_false(self):
        """Test supports_channel returns False for unsupported channels."""
        self.assertFalse(self.medium_event.supports_channel(NotificationChannel.SMS))
        self.assertFalse(self.medium_event.supports_channel(NotificationChannel.WEBSOCKET))


class TestNotificationEvents(unittest.TestCase):
    """Test NotificationEvents enum and registry."""
    
    def test_all_events_in_registry(self):
        """Test that all enum events are in the registry."""
        for event_enum in NotificationEvents:
            self.assertIn(event_enum, NOTIFICATION_EVENTS)
    
    def test_registry_event_names_match_enum_values(self):
        """Test that registry event names match enum values."""
        for event_enum, event_obj in NOTIFICATION_EVENTS.items():
            self.assertEqual(event_obj.name, event_enum.value)
    
    def test_critical_events_bypass_preferences(self):
        """Test that critical events in registry bypass preferences."""
        critical_events = [
            NotificationEvents.EMERGENCY_ALERT,
            NotificationEvents.SECURITY_BREACH
        ]
        
        for event_enum in critical_events:
            event_obj = NOTIFICATION_EVENTS[event_enum]
            self.assertTrue(event_obj.bypasses_preferences)
            self.assertEqual(event_obj.priority, NotificationPriority.CRITICAL)
    
    def test_non_critical_events_respect_preferences(self):
        """Test that non-critical events respect preferences."""
        non_critical_events = [
            NotificationEvents.VISITOR_ARRIVAL,
            NotificationEvents.PAYMENT_DUE,
            NotificationEvents.COMMENT_REPLY
        ]
        
        for event_enum in non_critical_events:
            event_obj = NOTIFICATION_EVENTS[event_enum]
            self.assertFalse(event_obj.bypasses_preferences)
            self.assertNotEqual(event_obj.priority, NotificationPriority.CRITICAL)


class TestEventUtilityFunctions(unittest.TestCase):
    """Test utility functions for event management."""
    
    def test_get_event_success(self):
        """Test get_event returns correct event object."""
        event = get_event(NotificationEvents.EMERGENCY_ALERT)
        self.assertEqual(event.name, "emergency_alert")
        self.assertEqual(event.priority, NotificationPriority.CRITICAL)
    
    def test_get_event_keyerror(self):
        """Test get_event raises KeyError for invalid event."""
        # Create a mock enum value that's not in registry
        class MockEnum:
            value = "nonexistent_event"
        
        with self.assertRaises(KeyError):
            get_event(MockEnum())
    
    def test_get_events_by_priority(self):
        """Test get_events_by_priority returns correct events."""
        critical_events = get_events_by_priority(NotificationPriority.CRITICAL)
        
        # Should have at least emergency alert and security breach
        self.assertGreaterEqual(len(critical_events), 2)
        
        for event in critical_events:
            self.assertEqual(event.priority, NotificationPriority.CRITICAL)
            self.assertTrue(event.bypasses_preferences)
    
    def test_get_critical_events(self):
        """Test get_critical_events returns only critical events."""
        critical_events = get_critical_events()
        
        self.assertGreater(len(critical_events), 0)
        
        for event in critical_events:
            self.assertTrue(event.bypasses_preferences)
            self.assertEqual(event.priority, NotificationPriority.CRITICAL)
    
    def test_priority_level_determination(self):
        """Test that priority levels are correctly determined."""
        # Test each priority level
        priorities = [
            NotificationPriority.CRITICAL,
            NotificationPriority.HIGH,
            NotificationPriority.MEDIUM,
            NotificationPriority.LOW
        ]
        
        for priority in priorities:
            events = get_events_by_priority(priority)
            for event in events:
                self.assertEqual(event.priority, priority)
                self.assertEqual(event.priority_level, priority.name)


if __name__ == '__main__':
    unittest.main()