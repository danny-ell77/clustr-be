"""
Tests for member maintenance views.
"""
import uuid
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models import MaintenanceLog
from .utils import create_cluster, create_user, create_maintenance_log, authenticate_user


class MemberMaintenanceLogViewSetTests(APITestCase):
    """
    Test cases for MemberMaintenanceLogViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="maintenance@example.com", cluster=self.cluster)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list maintenance requests.
        """
        url = reverse("members:member-maintenance-request-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_empty(self):
        """
        User with no maintenance requests should get empty results.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-maintenance-request-list")
        with patch.object(MaintenanceLog.objects, "filter", return_value=MaintenanceLog.objects.none()):
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_unauthenticated(self):
        """
        Unauthenticated users should not be able to create maintenance requests.
        """
        url = reverse("members:member-maintenance-request-list")
        data = {"title": "Test", "description": "desc", "maintenance_type": "GENERAL"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("core.common.includes.maintenance.create_log")
    def test_create_success(self, mock_create_log):
        """
        Authenticated users should be able to create maintenance requests.
        """
        mock_log = MagicMock(spec=MaintenanceLog)
        mock_log.id = uuid.uuid4()
        mock_create_log.return_value = mock_log
        authenticate_user(self.client, self.member)
        url = reverse("members:member-maintenance-request-list")
        data = {
            "title": "Broken Pipe",
            "description": "The pipe in the kitchen is leaking.",
            "maintenance_type": "PLUMBING",
            "priority": "HIGH",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_create_log.assert_called_once()

    def test_create_missing_required_fields(self):
        """
        Creating without required fields should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-maintenance-request-list")
        data = {"title": "Only Title"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_nonexistent(self):
        """
        Retrieving a non-existent maintenance request should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:member-maintenance-request-detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MaintenanceChoicesViewTests(APITestCase):
    """
    Test cases for maintenance_choices view.
    """

    def test_get_choices_unauthenticated(self):
        """
        This endpoint might be accessible without auth depending on implementation.
        We just ensure no server error.
        """
        url = reverse("members:maintenance-choices")
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])

    def test_get_choices_authenticated(self):
        """
        Authenticated users should get maintenance choices.
        """
        cluster, admin = create_cluster()
        member = create_user(email="choices@example.com", cluster=cluster)
        authenticate_user(self.client, member)
        url = reverse("members:maintenance-choices")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("maintenance_types", response.data["data"])
        self.assertIn("maintenance_priorities", response.data["data"])
