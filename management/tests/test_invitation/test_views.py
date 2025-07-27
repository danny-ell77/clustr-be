
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import create_user, create_cluster, create_visitor, create_invitation
from core.common.models import Invitation


class ManagementInvitationViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.visitor = create_visitor(self.cluster, self.admin_user)
        self.invitation = create_invitation(
            self.cluster, self.visitor, self.admin_user
        )

    def test_list_invitations_authenticated_with_permission(self):
        """
        Ensure users with permission can list invitations.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_invitation_authenticated_with_permission(self):
        """
        Ensure users with permission can create an invitation.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-list")
        data = {
            "visitor": self.visitor.pk,
            "title": "New Invitation",
            "start_date": "2025-12-25",
            "end_date": "2025-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_revoke_invitation(self):
        """
        Ensure an invitation can be revoked.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-revoke", kwargs={"pk": self.invitation.pk})
        data = {"revocation_reason": "Test reason"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.REVOKED)

    def test_retrieve_invitation(self):
        """
        Ensure an admin can retrieve an invitation.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-detail", kwargs={"pk": self.invitation.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_invitation(self):
        """
        Ensure an admin can update an invitation.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-detail", kwargs={"pk": self.invitation.pk})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.title, "Updated Title")

    def test_delete_invitation(self):
        """
        Ensure an admin can delete an invitation.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:invitation-detail", kwargs={"pk": self.invitation.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
