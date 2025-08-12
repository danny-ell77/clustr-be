"""
Tests for visitor notification functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountUser
from core.common.models import Visitor, VisitorLog, Cluster
from core.notifications.events import NotificationEvents
from core.common.includes import notifications


class VisitorNotificationTestCase(TestCase):
    """Test visitor notification functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test cluster
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street"
        )

        # Create test users
        self.inviting_user = AccountUser.objects.create(
            email_address="resident@test.com",
            first_name="John",
            last_name="Resident",
            cluster=self.cluster
        )

        self.security_user = AccountUser.objects.create(
            email_address="security@test.com",
            first_name="Security",
            last_name="Guard",
            cluster=self.cluster,
            role="SECURITY"
        )

        # Create test visitor
        self.visitor = Visitor.objects.create(
            name="Jane Visitor",
            phone="+1234567890",
            email="visitor@test.com",
            estimated_arrival=timezone.now() + timedelta(hours=1),
            visit_type=Visitor.VisitType.ONE_TIME,
            invited_by=self.inviting_user.id,
            cluster=self.cluster,
            valid_date=(timezone.now() + timedelta(days=1)).date(),
            access_code="ABC123"
        )

    @patch('core.notifications.manager.NotificationManager.send')
    def test_visitor_arrival_notification(self, mock_send):
        """Test that visitor arrival notification is sent correctly."""
        mock_send.return_value = True

        # Create visitor log (simulating check-in)
        log = VisitorLog.objects.create(
            visitor=self.visitor,
            log_type=VisitorLog.LogType.CHECKED_IN,
            checked_in_by=self.security_user.id,
            cluster=self.cluster
        )

        # Simulate the notification call from the view
        notifications.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[self.inviting_user],
            cluster=self.visitor.cluster,
            context={
                "visitor_name": self.visitor.name,
                "access_code": self.visitor.access_code,
                "arrival_time": log.created_at,
                "unit": getattr(self.inviting_user, 'unit', 'N/A'),
                "checked_in_by": self.security_user.get_full_name(),
            }
        )

        # Verify notification was called
        mock_send.assert_called_once_with(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[self.inviting_user],
            cluster=self.visitor.cluster,
            context={
                "visitor_name": "Jane Visitor",
                "access_code": "ABC123",
                "arrival_time": log.created_at,
                "unit": "N/A",
                "checked_in_by": "Security Guard",
            }
        )

    @patch('core.notifications.manager.NotificationManager.send')
    def test_visitor_overstay_notification(self, mock_send):
        """Test that visitor overstay notification is sent correctly."""
        mock_send.return_value = True

        # Create check-in log from 6 hours ago (overstay for one-time visit)
        checkin_time = timezone.now() - timedelta(hours=6)
        VisitorLog.objects.create(
            visitor=self.visitor,
            log_type=VisitorLog.LogType.CHECKED_IN,
            checked_in_by=self.security_user.id,
            cluster=self.cluster,
            created_at=checkin_time
        )

        # Update visitor status to checked in
        self.visitor.status = Visitor.Status.CHECKED_IN
        self.visitor.save()

        # Simulate overstay notification
        overstay_duration = timedelta(hours=2)  # 6 hours - 4 hours expected
        
        notifications.send(
            event_name=NotificationEvents.VISITOR_OVERSTAY,
            recipients=[self.inviting_user, self.security_user],
            cluster=self.visitor.cluster,
            context={
                "visitor_name": self.visitor.name,
                "visitor_phone": self.visitor.phone,
                "invited_by": self.inviting_user.get_full_name(),
                "overstay_duration": str(overstay_duration).split('.')[0],
                "visit_type": self.visitor.get_visit_type_display(),
                "access_code": self.visitor.access_code,
                "checkin_time": checkin_time,
            }
        )

        # Verify notification was called
        mock_send.assert_called_once_with(
            event_name=NotificationEvents.VISITOR_OVERSTAY,
            recipients=[self.inviting_user, self.security_user],
            cluster=self.visitor.cluster,
            context={
                "visitor_name": "Jane Visitor",
                "visitor_phone": "+1234567890",
                "invited_by": "John Resident",
                "overstay_duration": "2:00:00",
                "visit_type": "One-time",
                "access_code": "ABC123",
                "checkin_time": checkin_time,
            }
        )

    def test_visitor_arrival_context_data(self):
        """Test that visitor arrival context data is properly formatted."""
        log = VisitorLog.objects.create(
            visitor=self.visitor,
            log_type=VisitorLog.LogType.CHECKED_IN,
            checked_in_by=self.security_user.id,
            cluster=self.cluster
        )

        context = {
            "visitor_name": self.visitor.name,
            "access_code": self.visitor.access_code,
            "arrival_time": log.created_at,
            "unit": getattr(self.inviting_user, 'unit', 'N/A'),
            "checked_in_by": self.security_user.get_full_name(),
        }

        # Verify context contains expected fields
        self.assertEqual(context["visitor_name"], "Jane Visitor")
        self.assertEqual(context["access_code"], "ABC123")
        self.assertEqual(context["unit"], "N/A")
        self.assertEqual(context["checked_in_by"], "Security Guard")
        self.assertIsInstance(context["arrival_time"], datetime)

    def test_visitor_overstay_context_data(self):
        """Test that visitor overstay context data is properly formatted."""
        checkin_time = timezone.now() - timedelta(hours=6)
        overstay_duration = timedelta(hours=2)

        context = {
            "visitor_name": self.visitor.name,
            "visitor_phone": self.visitor.phone,
            "invited_by": self.inviting_user.get_full_name(),
            "overstay_duration": str(overstay_duration).split('.')[0],
            "visit_type": self.visitor.get_visit_type_display(),
            "access_code": self.visitor.access_code,
            "checkin_time": checkin_time,
        }

        # Verify context contains expected fields
        self.assertEqual(context["visitor_name"], "Jane Visitor")
        self.assertEqual(context["visitor_phone"], "+1234567890")
        self.assertEqual(context["invited_by"], "John Resident")
        self.assertEqual(context["overstay_duration"], "2:00:00")
        self.assertEqual(context["visit_type"], "One-time")
        self.assertEqual(context["access_code"], "ABC123")
        self.assertIsInstance(context["checkin_time"], datetime)