"""
Tests for member invitation views.
"""
import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models import Invitation
from .utils import create_cluster, create_user, create_invitation, authenticate_user


class MemberInvitationViewSetTests(APITestCase):
    """
    Test cases for MemberInvitationViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="invitation@example.com", cluster=self.cluster)
        self.invitation = create_invitation(self.member)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list invitations.
        """
        url = reverse("members:member-invitation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_invitations(self):
        """
        User should only see their own invitations.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_does_not_show_other_users_invitations(self):
        """
        User should not see invitations created by other users.
        """
        other_user = create_user(email="otherinvite@example.com", cluster=self.cluster)
        create_invitation(other_user, title="Other Guest")
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_invitation(self):
        """
        User should be able to create an invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-list")
        data = {
            "title": "New Invitation",
            "visitor": str(self.invitation.visitor.id),
            "start_date": "2025-12-25",
            "end_date": "2026-01-01",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Invitation.objects.filter(title="New Invitation", created_by=self.member.id).exists())

    def test_create_invitation_missing_required_fields(self):
        """
        Creating an invitation without required fields should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-list")
        data = {"title": "Incomplete"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_own_invitation(self):
        """
        User should be able to retrieve their own invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-detail", kwargs={"pk": str(self.invitation.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.invitation.id))

    def test_retrieve_other_users_invitation(self):
        """
        User should not be able to retrieve other user's invitation.
        """
        other_user = create_user(email="otherinviteret@example.com", cluster=self.cluster)
        other_invitation = create_invitation(other_user)
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-detail", kwargs={"pk": str(other_invitation.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_invitation(self):
        """
        Retrieving non-existent invitation should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:member-invitation-detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_invitation(self):
        """
        User should be able to revoke an active invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-revoke", kwargs={"pk": str(self.invitation.id)})
        data = {"revocation_reason": "No longer needed."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.REVOKED)

    def test_revoke_already_revoked_fails(self):
        """
        Revoking an already revoked invitation should fail.
        """
        self.invitation.status = Invitation.Status.REVOKED
        self.invitation.save()
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-revoke", kwargs={"pk": str(self.invitation.id)})
        data = {"revocation_reason": "Trying again."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_invitation(self):
        """
        User should be able to update their invitation.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:member-invitation-detail", kwargs={"pk": str(self.invitation.id)})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.title, "Updated Title")
