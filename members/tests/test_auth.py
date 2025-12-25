"""
Tests for member authentication views.
"""
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from accounts.models import AccountUser
from .utils import create_cluster, create_user, authenticate_user, MOCK_USER_PWD
from unittest.mock import patch

class MemberRegistrationViewTests(APITestCase):
    """
    Test cases for MemberRegistrationView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()

    @patch('core.common.email_sender.AccountEmailSender.send')
    def test_registration_success(self, mock_email_sender):
        """
        A new member should be able to register successfully with valid data.
        """
        url = reverse("members:register")
        data = {
            "email_address": "newmember@example.com",
            "name": "New Member",
            "phone_number": "+2348012345678",
            "unit_address": "Unit 101, Block A",
            "password": "StrongP@ss123!",
            "confirm_password": "StrongP@ss123!",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertTrue(AccountUser.objects.filter(email_address="newmember@example.com").exists())

    def test_registration_passwords_mismatch(self):
        """
        Registration should fail if passwords do not match.
        """
        url = reverse("members:register")
        data = {
            "email_address": "mismatch@example.com",
            "name": "Mismatch User",
            "phone_number": "+2348012345678",
            "unit_address": "Unit 101",
            "password": "StrongP@ss123!",
            "confirm_password": "DifferentP@ss123!",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_registration_duplicate_email(self):
        """
        Registration should fail if email already exists.
        """
        create_user(email="existing@example.com", cluster=self.cluster)
        url = reverse("members:register")
        data = {
            "email_address": "existing@example.com",
            "name": "Duplicate User",
            "phone_number": "+2348012345679",
            "unit_address": "Unit 102",
            "password": "StrongP@ss123!",
            "confirm_password": "StrongP@ss123!",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_required_fields(self):
        """
        Registration should fail if required fields are missing.
        """
        url = reverse("members:register")
        data = {
            "email_address": "partial@example.com",
            "name": "Partial User",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_invalid_email_format(self):
        """
        Registration should fail if email format is invalid.
        """
        url = reverse("members:register")
        data = {
            "email_address": "invalid-email",
            "name": "Invalid Email User",
            "phone_number": "+2348012345678",
            "unit_address": "Unit 103",
            "password": "StrongP@ss123!",
            "confirm_password": "StrongP@ss123!",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_invalid_phone_format(self):
        """
        Registration should fail if phone format is invalid (not E.164).
        """
        url = reverse("members:register")
        data = {
            "email_address": "invalidphone@example.com",
            "name": "Invalid Phone User",
            "phone_number": "1234567890",
            "unit_address": "Unit 104",
            "password": "StrongP@ss123!",
            "confirm_password": "StrongP@ss123!",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_weak_password(self):
        """
        Registration should fail if password is too weak.
        """
        url = reverse("members:register")
        data = {
            "email_address": "weakpass@example.com",
            "name": "Weak Password User",
            "phone_number": "+2348012345678",
            "unit_address": "Unit 105",
            "password": "123",
            "confirm_password": "123",
            "cluster_id": str(self.cluster.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_invalid_cluster_id(self):
        """
        Registration should fail if cluster_id does not exist.
        """
        url = reverse("members:register")
        data = {
            "email_address": "badcluster@example.com",
            "name": "Bad Cluster User",
            "phone_number": "+2348012345678",
            "unit_address": "Unit 106",
            "password": "StrongP@ss123!",
            "confirm_password": "StrongP@ss123!",
            "cluster_id": "00000000-0000-0000-0000-000000000000",
        }
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])


class MemberLoginViewTests(APITestCase):
    """
    Test cases for MemberLoginView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="member@example.com", cluster=self.cluster)

    def test_login_success(self):
        """
        A member should be able to login with valid credentials.
        """
        url = reverse("members:login")
        data = {
            "email_address": self.member.email_address,
            "password": MOCK_USER_PWD,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_login_invalid_password(self):
        """
        Login should fail with an incorrect password.
        """
        url = reverse("members:login")
        data = {
            "email_address": self.member.email_address,
            "password": "WrongPassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        """
        Login should fail if user does not exist.
        """
        url = reverse("members:login")
        data = {
            "email_address": "nonexistent@example.com",
            "password": "SomePassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_email(self):
        """
        Login should fail if email is missing.
        """
        url = reverse("members:login")
        data = {"password": MOCK_USER_PWD}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        """
        Login should fail if password is missing.
        """
        url = reverse("members:login")
        data = {"email_address": self.member.email_address}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_empty_body(self):
        """
        Login should fail with an empty request body.
        """
        url = reverse("members:login")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
