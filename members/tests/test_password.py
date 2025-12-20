"""
Tests for member password management views.
"""
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from accounts.models import UserVerification, VerifyMode, VerifyReason
from .utils import create_cluster, create_user, authenticate_user, MOCK_USER_PWD


class ChangePasswordViewTests(APITestCase):
    """
    Test cases for ChangePasswordView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="changepass@example.com", cluster=self.cluster)

    def test_change_password_unauthenticated(self):
        """
        Unauthenticated users should not be able to change password.
        """
        url = reverse("members:change_password")
        data = {
            "current_password": MOCK_USER_PWD,
            "new_password": "NewStrongP@ss123!",
            "confirm_password": "NewStrongP@ss123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_success(self):
        """
        User should be able to change password with valid credentials.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:change_password")
        new_password = "NewStrongP@ss123!"
        data = {
            "current_password": MOCK_USER_PWD,
            "new_password": new_password,
            "confirm_password": new_password,
        }
        response = self.client.post(url, data, format="json")
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password(new_password))

    def test_change_password_wrong_current_password(self):
        """
        Changing password should fail with wrong current password.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:change_password")
        data = {
            "current_password": "WrongCurrentP@ss!",
            "new_password": "NewStrongP@ss123!",
            "confirm_password": "NewStrongP@ss123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch_new_passwords(self):
        """
        Changing password should fail if new passwords don't match.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:change_password")
        data = {
            "current_password": MOCK_USER_PWD,
            "new_password": "NewStrongP@ss123!",
            "confirm_password": "DifferentP@ss123!",
        }
        response = self.client.post(url, data, format="json")
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_missing_fields(self):
        """
        Changing password should fail if required fields are missing.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:change_password")
        data = {"current_password": MOCK_USER_PWD}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RequestPasswordResetViewTests(APITestCase):
    """
    Test cases for RequestPasswordResetView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="resetrequest@example.com", cluster=self.cluster)

    @patch("accounts.models.email_verification.UserVerification.send_mail")
    def test_request_reset_success(self, mock_send_mail):
        """
        Requesting password reset should always return success.
        """
        url = reverse("members:request_password_reset")
        data = {"email": self.member.email_address}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()

    def test_request_reset_nonexistent_email(self):
        """
        Requesting reset for non-existent email should still return success (security).
        """
        url = reverse("members:request_password_reset")
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_reset_missing_email(self):
        """
        Requesting reset without email should fail.
        """
        url = reverse("members:request_password_reset")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResetPasswordViewTests(APITestCase):
    """
    Test cases for ResetPasswordView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="resetpass@example.com", cluster=self.cluster)
        self.verification = UserVerification.for_mode(
            VerifyMode.OTP, self.member, VerifyReason.PASSWORD_RESET
        )

    def test_reset_password_success(self):
        """
        Password should be reset with a valid verification key.
        """
        url = reverse("members:reset_password")
        new_password = "ResetStrongP@ss123!"
        data = {
            "verification_key": self.verification.otp,
            "password": new_password,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password(new_password))

    def test_reset_password_invalid_key(self):
        """
        Resetting password should fail with an invalid verification key.
        """
        url = reverse("members:reset_password")
        data = {
            "verification_key": "invalid123",
            "password": "NewStrongP@ss123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_missing_verification_key(self):
        """
        Resetting password should fail without verification key.
        """
        url = reverse("members:reset_password")
        data = {"password": "NewStrongP@ss123!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_missing_password(self):
        """
        Resetting password should fail without new password.
        """
        url = reverse("members:reset_password")
        data = {"verification_key": self.verification.otp}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_used_key(self):
        """
        Resetting password should fail with an already used verification key.
        """
        self.verification.is_used = True
        self.verification.save()
        url = reverse("members:reset_password")
        data = {
            "verification_key": self.verification.otp,
            "password": "NewStrongP@ss123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
