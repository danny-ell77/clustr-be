"""
Tests for member visitor views.
"""
import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models import Visitor
from .utils import create_cluster, create_user, create_visitor, authenticate_user


class MemberVisitorViewSetTests(APITestCase):
    """
    Test cases for MemberVisitorViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="visitor@example.com", cluster=self.cluster)
        self.visitor = create_visitor(self.member)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list visitors.
        """
        url = reverse("members:member-visitor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_visitors(self):
        """
        User should only see visitors they invited.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_does_not_show_other_users_visitors(self):
        """
        User should not see visitors invited by other users.
        """
        other_user = create_user(email="othervisitor@example.com", cluster=self.cluster)
        create_visitor(other_user, name="Other Visitor")
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_visitor(self):
        """
        User should be able to create a visitor invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-list")
        data = {
            "name": "New Visitor",
            "phone_number": "+2348000000020",
            "purpose": "Delivery",
            "expected_arrival": "2025-12-25T14:00:00Z",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Visitor.objects.filter(name="New Visitor", invited_by_id=self.member.id).exists())

    def test_create_visitor_missing_required_fields(self):
        """
        Creating a visitor without required fields should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-list")
        data = {"name": "Incomplete Visitor"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_own_visitor(self):
        """
        User should be able to retrieve their own visitor.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-detail", kwargs={"pk": str(self.visitor.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.visitor.id))

    def test_retrieve_other_users_visitor(self):
        """
        User should not be able to retrieve other user's visitor.
        """
        other_user = create_user(email="othervisitorret@example.com", cluster=self.cluster)
        other_visitor = create_visitor(other_user)
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-detail", kwargs={"pk": str(other_visitor.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_visitor(self):
        """
        Retrieving non-existent visitor should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:member-visitor-detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_invitation(self):
        """
        User should be able to revoke a visitor invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-revoke-invitation", kwargs={"pk": str(self.visitor.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.visitor.refresh_from_db()
        self.assertEqual(self.visitor.status, Visitor.Status.REJECTED)

    def test_revoke_already_checked_in_fails(self):
        """
        Revoking a visitor who has already checked in should fail.
        """
        self.visitor.status = Visitor.Status.CHECKED_IN
        self.visitor.save()
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-revoke-invitation", kwargs={"pk": str(self.visitor.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MemberVisitorLogViewSetTests(APITestCase):
    """
    Test cases for MemberVisitorLogViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="visitorlog@example.com", cluster=self.cluster)
        self.visitor = create_visitor(self.member)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list visitor logs.
        """
        url = reverse("members:member-visitor-log-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_visitor_logs(self):
        """
        User should be able to list visitor logs for their visitors.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-visitor-log-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
