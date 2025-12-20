"""
Tests for member phone verification views.
"""
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from accounts.models import UserVerification, VerifyMode, VerifyReason
from .utils import create_cluster, create_user, authenticate_user


class RequestPhoneVerificationViewTests(APITestCase):
    """
    Test cases for RequestPhoneVerificationView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="phone@example.com", cluster=self.cluster)

    def test_request_unauthenticated(self):
        """
        Unauthenticated users should not be able to request phone verification.
        """
        url = reverse("members:request_phone_verification")
        response = self.client.post(url, {"phone_number": "+2348000000000"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.models.sms_sender.SMSSender.send_verification_code")
    def test_request_success(self, mock_send_sms):
        """
        A valid request should trigger SMS sending.
        """
        mock_send_sms.return_value = True
        authenticate_user(self.client, self.member)
        url = reverse("members:request_phone_verification")
        response = self.client.post(url, {"phone_number": "+2348000000099"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_sms.assert_called_once()
        self.member.refresh_from_db()
        self.assertEqual(self.member.phone_number, "+2348000000099")
        self.assertFalse(self.member.is_phone_verified)

    def test_request_missing_phone_number(self):
        """
        Request should fail if phone_number is missing.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:request_phone_verification")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.models.sms_sender.SMSSender.send_verification_code")
    def test_request_sms_failure(self, mock_send_sms):
        """
        If SMS sending fails, an error response should be returned.
        """
        mock_send_sms.return_value = False
        authenticate_user(self.client, self.member)
        url = reverse("members:request_phone_verification")
        response = self.client.post(url, {"phone_number": "+2348000000099"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPhoneViewTests(APITestCase):
    """
    Test cases for VerifyPhoneView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="verifyphone@example.com", cluster=self.cluster)
        self.member.phone_number = "+2348111222333"
        self.member.is_phone_verified = False
        self.member.save()

    def test_verify_unauthenticated(self):
        """
        Unauthenticated users should not be able to verify phone.
        """
        url = reverse("members:verify_phone")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_success(self):
        """
        Verification should succeed with valid OTP.
        """
        verification = UserVerification.for_mode(
            VerifyMode.SMS, self.member, VerifyReason.PHONE_VERIFICATION
        )
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_phone")
        data = {
            "phone_number": self.member.phone_number,
            "verification_code": verification.otp,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_phone_verified)
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_verify_invalid_code(self):
        """
        Verification should fail with an invalid code.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_phone")
        data = {
            "phone_number": self.member.phone_number,
            "verification_code": "000000",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_phone_number_mismatch(self):
        """
        Verification should fail if phone number does not match account.
        """
        verification = UserVerification.for_mode(
            VerifyMode.SMS, self.member, VerifyReason.PHONE_VERIFICATION
        )
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_phone")
        data = {
            "phone_number": "+2349999999999",
            "verification_code": verification.otp,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_missing_fields(self):
        """
        Verification should fail if required fields are missing.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_phone")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
