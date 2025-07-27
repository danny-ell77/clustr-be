"""
Tests for emergency management models.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch

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


class EmergencyContactModelTest(TestCase):
    """Test cases for EmergencyContact model"""
    
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
    
    def test_create_personal_emergency_contact(self):
        """Test creating a personal emergency contact"""
        contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="John Doe",
            phone_number="+1234567890",
            email="john@example.com",
            emergency_types=[EmergencyType.HEALTH, EmergencyType.THEFT],
            contact_type=EmergencyContactType.PERSONAL,
            user=self.user,
            is_active=True,
            is_primary=True
        )
        
        self.assertEqual(contact.name, "John Doe")
        self.assertEqual(contact.phone_number, "+1234567890")
        self.assertEqual(contact.email, "john@example.com")
        self.assertEqual(contact.emergency_types, [EmergencyType.HEALTH, EmergencyType.THEFT])
        self.assertEqual(contact.contact_type, EmergencyContactType.PERSONAL)
        self.assertEqual(contact.user, self.user)
        self.assertTrue(contact.is_active)
        self.assertTrue(contact.is_primary)
    
    def test_create_estate_wide_emergency_contact(self):
        """Test creating an estate-wide emergency contact"""
        contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Security Office",
            phone_number="+1234567890",
            emergency_types=[EmergencyType.SECURITY, EmergencyType.THEFT],
            contact_type=EmergencyContactType.ESTATE_WIDE,
            is_active=True
        )
        
        self.assertEqual(contact.name, "Security Office")
        self.assertEqual(contact.contact_type, EmergencyContactType.ESTATE_WIDE)
        self.assertIsNone(contact.user)
        self.assertTrue(contact.is_active)
    
    def test_emergency_contact_str_representation(self):
        """Test string representation of emergency contact"""
        contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Test Contact",
            phone_number="+1234567890",
            emergency_types=[EmergencyType.HEALTH],
            contact_type=EmergencyContactType.PERSONAL,
            user=self.user
        )
        
        expected_str = "Test Contact (Personal Contact)"
        self.assertEqual(str(contact), expected_str)
    
    def test_get_emergency_types_display(self):
        """Test getting display names for emergency types"""
        contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Test Contact",
            phone_number="+1234567890",
            emergency_types=[EmergencyType.HEALTH, EmergencyType.FIRE],
            contact_type=EmergencyContactType.PERSONAL,
            user=self.user
        )
        
        display_types = contact.get_emergency_types_display()
        self.assertIn("Health Emergency", display_types)
        self.assertIn("Fire Emergency", display_types)
    
    def test_handles_emergency_type(self):
        """Test checking if contact handles specific emergency type"""
        contact = EmergencyContact.objects.create(
            cluster=self.cluster,
            name="Test Contact",
            phone_number="+1234567890",
            emergency_types=[EmergencyType.HEALTH, EmergencyType.FIRE],
            contact_type=EmergencyContactType.PERSONAL,
            user=self.user
        )
        
        self.assertTrue(contact.handles_emergency_type(EmergencyType.HEALTH))
        self.assertTrue(contact.handles_emergency_type(EmergencyType.FIRE))
        self.assertFalse(contact.handles_emergency_type(EmergencyType.THEFT))


class SOSAlertModelTest(TestCase):
    """Test cases for SOSAlert model"""
    
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
    
    def test_create_sos_alert(self):
        """Test creating an SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            description="Medical emergency",
            location="Building A, Apt 101",
            priority="critical"
        )
        
        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.emergency_type, EmergencyType.HEALTH)
        self.assertEqual(alert.description, "Medical emergency")
        self.assertEqual(alert.location, "Building A, Apt 101")
        self.assertEqual(alert.priority, "critical")
        self.assertEqual(alert.status, EmergencyStatus.ACTIVE)
        self.assertIsNotNone(alert.alert_id)
    
    def test_alert_id_generation(self):
        """Test automatic alert ID generation"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        self.assertIsNotNone(alert.alert_id)
        self.assertTrue(alert.alert_id.startswith("SOS-"))
    
    def test_sos_alert_str_representation(self):
        """Test string representation of SOS alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH,
            alert_id="SOS-TEST123"
        )
        
        expected_str = "SOS Alert SOS-TEST123 - Health Emergency"
        self.assertEqual(str(alert), expected_str)
    
    def test_is_active_property(self):
        """Test is_active property"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        # Initially active
        self.assertTrue(alert.is_active)
        
        # After acknowledgment, still active
        alert.status = EmergencyStatus.ACKNOWLEDGED
        self.assertTrue(alert.is_active)
        
        # After response started, still active
        alert.status = EmergencyStatus.RESPONDING
        self.assertTrue(alert.is_active)
        
        # After resolution, not active
        alert.status = EmergencyStatus.RESOLVED
        self.assertFalse(alert.is_active)
        
        # After cancellation, not active
        alert.status = EmergencyStatus.CANCELLED
        self.assertFalse(alert.is_active)
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        alert.acknowledge(self.responder)
        
        self.assertEqual(alert.status, EmergencyStatus.ACKNOWLEDGED)
        self.assertEqual(alert.acknowledged_by, self.responder)
        self.assertIsNotNone(alert.acknowledged_at)
    
    def test_start_response(self):
        """Test starting response to an alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        alert.start_response(self.responder)
        
        self.assertEqual(alert.status, EmergencyStatus.RESPONDING)
        self.assertEqual(alert.responded_by, self.responder)
        self.assertIsNotNone(alert.responded_at)
    
    def test_resolve_alert(self):
        """Test resolving an alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        resolution_notes = "Issue resolved successfully"
        alert.resolve(self.responder, resolution_notes)
        
        self.assertEqual(alert.status, EmergencyStatus.RESOLVED)
        self.assertEqual(alert.resolved_by, self.responder)
        self.assertEqual(alert.resolution_notes, resolution_notes)
        self.assertIsNotNone(alert.resolved_at)
    
    def test_cancel_alert(self):
        """Test cancelling an alert"""
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        
        cancellation_reason = "False alarm"
        alert.cancel(self.user, cancellation_reason)
        
        self.assertEqual(alert.status, EmergencyStatus.CANCELLED)
        self.assertEqual(alert.cancelled_by, self.user)
        self.assertEqual(alert.cancellation_reason, cancellation_reason)
        self.assertIsNotNone(alert.cancelled_at)
    
    @patch('django.utils.timezone.now')
    def test_response_time_calculation(self, mock_now):
        """Test response time calculation"""
        # Mock timezone.now() to return predictable times
        created_time = timezone.datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        response_time = timezone.datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        alert.created_at = created_time
        alert.responded_at = response_time
        alert.save()
        
        # Response time should be 5 minutes
        self.assertEqual(alert.response_time_minutes, 5)
    
    @patch('django.utils.timezone.now')
    def test_resolution_time_calculation(self, mock_now):
        """Test resolution time calculation"""
        # Mock timezone.now() to return predictable times
        created_time = timezone.datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        resolved_time = timezone.datetime(2023, 1, 1, 10, 15, 0, tzinfo=timezone.utc)
        
        alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
        alert.created_at = created_time
        alert.resolved_at = resolved_time
        alert.save()
        
        # Resolution time should be 15 minutes
        self.assertEqual(alert.resolution_time_minutes, 15)


class EmergencyResponseModelTest(TestCase):
    """Test cases for EmergencyResponse model"""
    
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
        
        self.alert = SOSAlert.objects.create(
            cluster=self.cluster,
            user=self.user,
            emergency_type=EmergencyType.HEALTH
        )
    
    def test_create_emergency_response(self):
        """Test creating an emergency response"""
        response = EmergencyResponse.objects.create(
            cluster=self.cluster,
            alert=self.alert,
            responder=self.responder,
            response_type="dispatched",
            notes="Response team dispatched",
            estimated_arrival=timezone.now() + timezone.timedelta(minutes=10)
        )
        
        self.assertEqual(response.alert, self.alert)
        self.assertEqual(response.responder, self.responder)
        self.assertEqual(response.response_type, "dispatched")
        self.assertEqual(response.notes, "Response team dispatched")
        self.assertIsNotNone(response.estimated_arrival)
    
    def test_emergency_response_str_representation(self):
        """Test string representation of emergency response"""
        response = EmergencyResponse.objects.create(
            cluster=self.cluster,
            alert=self.alert,
            responder=self.responder,
            response_type="dispatched"
        )
        
        expected_str = f"Response to {self.alert.alert_id} by {self.responder.name}"
        self.assertEqual(str(response), expected_str)