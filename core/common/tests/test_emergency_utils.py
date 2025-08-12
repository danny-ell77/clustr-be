"""
Tests for emergency management utilities.
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock

from accounts.models import AccountUser
from core.common.models.cluster import Cluster
from core.common.models.emergency import (
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
    EmergencyStatus,
)
from core.common.includes import emergencies


class EmergencyManagerTest(TestCase):
    """Test cases for EmergencyManager utility"""
    
    def setUp(self):
        """Set up test data"""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.user = AccountUser.objects.create_user(
            email_address="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        self.user.clusters.add(self.cluster)
        
        self.responder = AccountUser.objects.create_user(
            email_address="responder@example.com",
            password="testpass123",
            first_name="Responder",
            last_name="User"
        )
        self.responder.clusters.add(self.cluster)
        
        # Create test emergency contacts
        self.personal_contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Personal Contact",
            phone_number="+1234567890",
            email="personal@example.com",
            emergency_types=[EmergencyType.HEALTH, EmergencyType.THEFT],
            contact_type=EmergencyContactType.PERSONAL,
            user=self.user,
            is_active=True,
            is_primary=True
        )
        
        self.estate_contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Estate Security",
            phone_number="+1234567891",
            email="security@example.com",
            emergency_types=[EmergencyType.SECURITY, EmergencyType.THEFT],
            contact_type=EmergencyContactType.ESTATE_WIDE,
            is_active=True,
            is_primary=True
        )
    
    def test_get_estate_emergency_contacts(self):
        """Test getting estate-wide emergency contacts"""
        contacts = emergencies.get_estate_emergency_contacts(self.cluster)
        
        # Should return only estate-wide contacts
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].name, "Estate Security")
    
    def test_get_estate_emergency_contacts_with_type_filter(self):
        """Test getting estate-wide emergency contacts with type filter"""
        contacts = emergencies.get_estate_emergency_contacts(
            self.cluster,
            EmergencyType.SECURITY
        )
        
        # Should return estate contacts that handle security
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].name, "Estate Security")
        
        # Test with type that estate contact doesn't handle
        contacts = emergencies.get_estate_emergency_contacts(
            self.cluster,
            EmergencyType.HEALTH
        )
        
        # Should return no contacts
        self.assertEqual(len(contacts), 0)
    
    @patch('core.common.utils.emergency_utils.emergencies.send_sos_alert_notifications')
    def test_create_sos_alert(self, mock_send_notifications):
        """Test creating an SOS alert"""
        alert = emergencies.create_alert(
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            description="Medical emergency",
            location="Building A",
            priority="critical"
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.emergency_type, EmergencyType.HEALTH)
        self.assertEqual(alert.description, "Medical emergency")
        self.assertEqual(alert.location, "Building A")
        self.assertEqual(alert.priority, "critical")
        self.assertEqual(alert.status, EmergencyStatus.ACTIVE)
        
        # Should have called send notifications
        mock_send_notifications.assert_called_once_with(alert)
    
    @patch('core.common.email_sender.AccountEmailSender.send')
    def test_send_sos_alert_notifications(self, mock_send):
        """Test sending SOS alert notifications"""
        mock_send.return_value = True
        
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            description="Robbery in progress"
        )
        
        emergencies.send_sos_alert_notifications(alert)
        
        # Should have attempted to send email
        mock_send.assert_called()
    
    def test_acknowledge_alert(self):
        """Test acknowledging an SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        result = emergencies.acknowledge_alert(alert, self.responder)
        
        self.assertTrue(result)
        alert.refresh_from_db()
        self.assertEqual(alert.status, EmergencyStatus.ACKNOWLEDGED)
        self.assertEqual(alert.acknowledged_by, self.responder)
        self.assertIsNotNone(alert.acknowledged_at)
    
    def test_start_response(self):
        """Test starting response to an SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        result = emergencies.start_response(alert, self.responder)
        
        self.assertTrue(result)
        alert.refresh_from_db()
        self.assertEqual(alert.status, EmergencyStatus.RESPONDING)
        self.assertEqual(alert.responded_by, self.responder)
        self.assertIsNotNone(alert.responded_at)
        
        # Should have created a response record
        response = EmergencyResponse.objects.filter(alert=alert).first()
        self.assertIsNotNone(response)
        self.assertEqual(response.responder, self.responder)
        self.assertEqual(response.response_type, 'dispatched')
    
    def test_resolve_alert(self):
        """Test resolving an SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        resolution_notes = "Issue resolved successfully"
        result = emergencies.resolve_alert(alert, self.responder, resolution_notes)
        
        self.assertTrue(result)
        alert.refresh_from_db()
        self.assertEqual(alert.status, EmergencyStatus.RESOLVED)
        self.assertEqual(alert.resolved_by, self.responder)
        self.assertEqual(alert.resolution_notes, resolution_notes)
        self.assertIsNotNone(alert.resolved_at)
        
        # Should have created a response record
        response = EmergencyResponse.objects.filter(alert=alert, response_type='resolved').first()
        self.assertIsNotNone(response)
        self.assertEqual(response.responder, self.responder)
    
    def test_cancel_alert(self):
        """Test cancelling an SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        cancellation_reason = "False alarm"
        result = emergencies.cancel_alert(alert, self.user, cancellation_reason)
        
        self.assertTrue(result)
        alert.refresh_from_db()
        self.assertEqual(alert.status, EmergencyStatus.CANCELLED)
        self.assertEqual(alert.cancelled_by, self.user)
        self.assertEqual(alert.cancellation_reason, cancellation_reason)
        self.assertIsNotNone(alert.cancelled_at)
        
        # Should have created a response record
        response = EmergencyResponse.objects.filter(alert=alert, response_type='cancelled').first()
        self.assertIsNotNone(response)
        self.assertEqual(response.responder, self.user)
    
    def test_get_active_alerts(self):
        """Test getting active alerts"""
        # Create alerts with different statuses
        active_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.ACTIVE
        )
        
        acknowledged_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            status=EmergencyStatus.ACKNOWLEDGED
        )
        
        responding_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.FIRE,
            status=EmergencyStatus.RESPONDING
        )
        
        resolved_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.SECURITY,
            status=EmergencyStatus.RESOLVED
        )
        
        active_alerts = emergencies.get_active_alerts(self.cluster)
        
        # Should return only active, acknowledged, and responding alerts
        self.assertEqual(len(active_alerts), 3)
        alert_ids = [alert.id for alert in active_alerts]
        self.assertIn(active_alert.id, alert_ids)
        self.assertIn(acknowledged_alert.id, alert_ids)
        self.assertIn(responding_alert.id, alert_ids)
        self.assertNotIn(resolved_alert.id, alert_ids)
    
    def test_get_user_alerts(self):
        """Test getting alerts for a specific user"""
        # Create alerts for different users
        user_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        other_user_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.responder,
            emergency_type=EmergencyType.THEFT
        )
        
        user_alerts = emergencies.get_user_alerts(self.user)
        
        # Should return only the user's alerts
        self.assertEqual(len(user_alerts), 1)
        self.assertEqual(user_alerts[0].id, user_alert.id)
    
    def test_get_user_alerts_with_status_filter(self):
        """Test getting user alerts with status filter"""
        # Create alerts with different statuses
        active_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.ACTIVE
        )
        
        resolved_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            status=EmergencyStatus.RESOLVED
        )
        
        # Get only active alerts
        active_alerts = emergencies.get_user_alerts(self.user, status=EmergencyStatus.ACTIVE)
        
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].id, active_alert.id)
        
        # Get only resolved alerts
        resolved_alerts = emergencies.get_user_alerts(self.user, status=EmergencyStatus.RESOLVED)
        
        self.assertEqual(len(resolved_alerts), 1)
        self.assertEqual(resolved_alerts[0].id, resolved_alert.id)
    
    def test_get_emergency_statistics(self):
        """Test getting emergency statistics"""
        # Create alerts with different statuses and types
        SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.ACTIVE
        )
        
        SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.RESOLVED
        )
        
        SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            status=EmergencyStatus.CANCELLED
        )
        
        stats = emergencies.get_emergency_statistics(self.cluster)
        
        self.assertEqual(stats['total_alerts'], 3)
        self.assertEqual(stats['active_alerts'], 1)
        self.assertEqual(stats['resolved_alerts'], 1)
        self.assertEqual(stats['cancelled_alerts'], 1)
        self.assertIn('Health Emergency', stats['alerts_by_type'])
        self.assertIn('Theft/Robbery', stats['alerts_by_type'])
        self.assertEqual(stats['alerts_by_type']['Health Emergency'], 2)
        self.assertEqual(stats['alerts_by_type']['Theft/Robbery'], 1)
    
    @patch('core.common.utils.emergency_utils.emergencies.check_user_emergency_permissions')
    def test_check_user_emergency_permissions(self, mock_check_permissions):
        """Test checking user emergency permissions"""
        mock_check_permissions.return_value = True
        
        result = emergencies.check_user_emergency_permissions(
            self.responder,
            EmergencyType.HEALTH
        )
        
        self.assertTrue(result)
        mock_check_permissions.assert_called_once_with(self.responder, EmergencyType.HEALTH)
    
    def test_generate_emergency_report(self):
        """Test generating emergency report"""
        # Create test alerts
        active_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.ACTIVE,
            priority='high'
        )
        
        resolved_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            status=EmergencyStatus.RESOLVED,
            priority='critical'
        )
        
        # Create response for resolved alert
        EmergencyResponse.objects.create(
            cluster=self.cluster,
            alert=resolved_alert,
            responder=self.responder,
            response_type='resolved',
            notes='Issue resolved successfully'
        )
        
        # Generate report
        report = emergencies.generate_emergency_report(self.cluster)
        
        # Verify report structure
        self.assertIn('report_generated_at', report)
        self.assertIn('summary', report)
        self.assertIn('time_analysis', report)
        self.assertIn('responder_analysis', report)
        self.assertIn('recent_alerts', report)
        
        # Verify summary data
        summary = report['summary']
        self.assertEqual(summary['total_alerts'], 2)
        self.assertIn('Health Emergency', summary['type_breakdown'])
        self.assertIn('Theft/Robbery', summary['type_breakdown'])
        self.assertEqual(summary['type_breakdown']['Health Emergency'], 1)
        self.assertEqual(summary['type_breakdown']['Theft/Robbery'], 1)
        
        # Verify recent alerts
        self.assertEqual(len(report['recent_alerts']), 2)
        
        # Verify responder analysis
        self.assertIn(self.responder.name, report['responder_analysis'])
        self.assertEqual(report['responder_analysis'][self.responder.name]['total_responses'], 1)
    
    def test_generate_emergency_report_with_filters(self):
        """Test generating emergency report with filters"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create alerts with different dates and types
        old_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            status=EmergencyStatus.RESOLVED
        )
        old_alert.created_at = timezone.now() - timedelta(days=10)
        old_alert.save(update_fields=["created_at"])
        
        recent_alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.THEFT,
            status=EmergencyStatus.ACTIVE
        )
        
        # Generate report with date filter
        start_date = timezone.now() - timedelta(days=5)
        report = emergencies.generate_emergency_report(
            self.cluster,
            start_date=start_date
        )
        
        # Should only include recent alert
        self.assertEqual(report['summary']['total_alerts'], 1)
        self.assertEqual(len(report['recent_alerts']), 1)
        self.assertEqual(report['recent_alerts'][0]['alert_id'], recent_alert.alert_id)
        
        # Generate report with emergency type filter
        report = emergencies.generate_emergency_report(
            self.cluster,
            emergency_type=EmergencyType.HEALTH
        )
        
        # Should only include health emergency
        self.assertEqual(report['summary']['total_alerts'], 1)
        self.assertEqual(report['recent_alerts'][0]['emergency_type'], 'Health Emergency')
    
    def test_generate_alert_incident_report(self):
        """Test generating incident report for specific alert"""
        # Create alert with full lifecycle
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            description='Medical emergency',
            location='Building A',
            priority='critical'
        )
        
        # Acknowledge alert
        emergencies.acknowledge_alert(alert, self.responder)
        
        # Start response
        emergencies.start_response(alert, self.responder)
        
        # Resolve alert
        emergencies.resolve_alert(alert, self.responder, 'Patient stabilized')
        
        # Generate incident report
        report = emergencies.generate_incident_report(alert)
        
        # Verify report structure
        self.assertIn('alert_info', report)
        self.assertIn('timeline', report)
        self.assertIn('metrics', report)
        self.assertIn('involved_contacts', report)
        self.assertIn('responses_summary', report)
        
        # Verify alert info
        alert_info = report['alert_info']
        self.assertEqual(alert_info['alert_id'], alert.alert_id)
        self.assertEqual(alert_info['emergency_type'], 'Health Emergency')
        self.assertEqual(alert_info['description'], 'Medical emergency')
        self.assertEqual(alert_info['location'], 'Building A')
        
        # Verify timeline has all events
        timeline = report['timeline']
        self.assertGreaterEqual(len(timeline), 4)  # Created, Acknowledged, Response Started, Resolved
        
        event_types = [event['event'] for event in timeline]
        self.assertIn('Alert Created', event_types)
        self.assertIn('Alert Acknowledged', event_types)
        self.assertIn('Response Started', event_types)
        self.assertIn('Alert Resolved', event_types)
        
        # Verify metrics
        metrics = report['metrics']
        self.assertIsNotNone(metrics['response_time_minutes'])
        self.assertIsNotNone(metrics['resolution_time_minutes'])
        self.assertGreater(metrics['total_responses'], 0)
        
        # Verify involved contacts
        self.assertGreater(len(report['involved_contacts']), 0)
    
    def test_generate_alert_incident_report_cancelled(self):
        """Test generating incident report for cancelled alert"""
        # Create and cancel alert
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            description='False alarm'
        )
        
        emergencies.cancel_alert(alert, self.user, 'Accidental trigger')
        
        # Generate incident report
        report = emergencies.generate_incident_report(alert)
        
        # Verify timeline includes cancellation
        timeline = report['timeline']
        event_types = [event['event'] for event in timeline]
        self.assertIn('Alert Created', event_types)
        self.assertIn('Alert Cancelled', event_types)
        
        # Find cancellation event
        cancellation_event = next(
            event for event in timeline if event['event'] == 'Alert Cancelled'
        )
        self.assertEqual(cancellation_event['user'], self.user.name)
        self.assertEqual(cancellation_event['details']['cancellation_reason'], 'Accidental trigger')