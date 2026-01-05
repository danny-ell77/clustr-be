from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AccountUser
from core.common.models import Cluster


class EmailVerificationEndpointTestCase(TestCase):
    """Test suite for the email verification endpoint"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create a test cluster
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            type="ESTATE"
        )
        
        # Create test users with different approval statuses
        self.approved_user = AccountUser.objects._create_user(
            email_address="approved@test.com",
            password="testpass123",
            name="Approved User",
            phone_number="+1234567890",
        )
        self.approved_user.approved_by_admin = True
        self.approved_user.is_verified = True
        self.approved_user.is_phone_verified = True
        self.approved_user.primary_cluster = self.cluster
        self.approved_user.save()
        
        self.pending_user = AccountUser.objects._create_user(
            email_address="pending@test.com",
            password="testpass123",
            name="Pending User",
            phone_number="+1234567891",
        )
        self.pending_user.approved_by_admin = False
        self.pending_user.is_verified = False
        self.pending_user.is_phone_verified = False
        self.pending_user.primary_cluster = self.cluster
        self.pending_user.save()
        
        self.partially_verified_user = AccountUser.objects._create_user(
            email_address="partial@test.com",
            password="testpass123",
            name="Partial User",
            phone_number="+1234567892",
        )
        self.partially_verified_user.approved_by_admin = False
        self.partially_verified_user.is_verified = True
        self.partially_verified_user.is_phone_verified = False
        self.partially_verified_user.primary_cluster = self.cluster
        self.partially_verified_user.save()

    def test_verify_existing_approved_account(self):
        """Test verification of existing approved account returns correct data"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "approved@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "approved@test.com")
        self.assertEqual(response.data["name"], "Approved User")
        self.assertTrue(response.data["approved_by_admin"])
        self.assertTrue(response.data["is_verified"])
        self.assertTrue(response.data["is_phone_verified"])
        self.assertEqual(response.data["next_step"], "signin")

    def test_verify_existing_pending_account(self):
        """Test verification of existing pending account returns correct data"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "pending@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "pending@test.com")
        self.assertEqual(response.data["name"], "Pending User")
        self.assertFalse(response.data["approved_by_admin"])
        self.assertFalse(response.data["is_verified"])
        self.assertFalse(response.data["is_phone_verified"])
        self.assertEqual(response.data["next_step"], "verify")

    def test_verify_partially_verified_account(self):
        """Test verification of account with partial verification status"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "partial@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "partial@test.com")
        self.assertEqual(response.data["name"], "Partial User")
        self.assertFalse(response.data["approved_by_admin"])
        self.assertTrue(response.data["is_verified"])
        self.assertFalse(response.data["is_phone_verified"])
        self.assertEqual(response.data["next_step"], "signin")

    def test_verify_nonexistent_account(self):
        """Test verification of nonexistent account returns 404"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "nonexistent@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "Account with this email does not exist"
        )

    def test_missing_email_field(self):
        """Test request with missing email field returns 400"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email_address", response.data)

    def test_invalid_email_format(self):
        """Test request with invalid email format returns 400"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "invalid-email"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email_address", response.data)

    def test_case_insensitive_email_lookup(self):
        """Test that email lookup is case-insensitive"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "APPROVED@TEST.COM"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "approved@test.com")
        self.assertEqual(response.data["name"], "Approved User")

    def test_whitespace_email_handling(self):
        """Test that email with leading/trailing whitespace is handled correctly"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "  approved@test.com  "
        }, format="json")
        
        # The serializer should validate and strip whitespace
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "approved@test.com")

    def test_public_endpoint_no_authentication_required(self):
        """Test that endpoint is accessible without authentication"""
        url = reverse("user-verify_account_by_email")
        # Ensure no authentication is set
        self.client.credentials()
        
        response = self.client.post(url, {
            "email_address": "approved@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_contains_only_expected_fields(self):
        """Test that response contains only the expected fields"""
        url = reverse("user-verify_account_by_email")
        response = self.client.post(url, {
            "email_address": "approved@test.com"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = {
            "name",
            "email_address",
            "approved_by_admin",
            "is_verified",
            "is_phone_verified",
            "next_step"
        }
        
        self.assertEqual(set(response.data.keys()), expected_fields)
        
        # Ensure sensitive fields are not exposed
        self.assertNotIn("password", response.data)
        self.assertNotIn("is_staff", response.data)
        self.assertNotIn("is_superuser", response.data)
        self.assertNotIn("phone_number", response.data)
