
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import (
    create_user,
    create_cluster,
    create_issue_ticket,
    create_issue_comment,
    create_issue_attachment,
)
from core.common.models import IssueStatus, IssuePriority


class ManagementIssueTicketViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.staff_user = create_user(
            email="staff@example.com", name="Staff User", is_cluster_staff=True
        )
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.staff_user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.issue_ticket = create_issue_ticket(self.cluster, self.user, self.staff_user)

    def test_list_issue_tickets_authenticated_with_permission(self):
        """
        Ensure staff and admin users can list issue tickets.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("management:issueticket-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_assign_issue_to_staff(self):
        """
        Ensure an admin can assign an issue to a staff member.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:issueticket-assign", kwargs={"pk": self.issue_ticket.pk})
        data = {"assigned_to": self.staff_user.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.issue_ticket.refresh_from_db()
        self.assertEqual(self.issue_ticket.assigned_to, self.staff_user)

    def test_escalate_issue(self):
        """
        Ensure an admin can escalate an issue.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:issueticket-escalate", kwargs={"pk": self.issue_ticket.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.issue_ticket.refresh_from_db()
        self.assertEqual(self.issue_ticket.priority, IssuePriority.URGENT)

    def test_get_issue_statistics(self):
        """
        Ensure issue statistics can be retrieved.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:issueticket-statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_issues", response.data)

    def test_retrieve_issue_ticket(self):
        """
        Ensure a staff user can retrieve an issue ticket.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("management:issueticket-detail", kwargs={"pk": self.issue_ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_issue_ticket(self):
        """
        Ensure a staff user can update an issue ticket.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("management:issueticket-detail", kwargs={"pk": self.issue_ticket.pk})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.issue_ticket.refresh_from_db()
        self.assertEqual(self.issue_ticket.title, "Updated Title")

    def test_delete_issue_ticket(self):
        """
        Ensure an admin can delete an issue ticket.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:issueticket-detail", kwargs={"pk": self.issue_ticket.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ManagementIssueCommentViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.staff_user = create_user(
            email="staff@example.com", name="Staff User", is_cluster_staff=True
        )
        self.user.clusters.add(self.cluster)
        self.staff_user.clusters.add(self.cluster)
        self.issue_ticket = create_issue_ticket(self.cluster, self.user, self.staff_user)
        self.comment = create_issue_comment(self.issue_ticket, self.user)

    def test_list_issue_comments(self):
        """
        Ensure comments for an issue can be listed.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issuecomment-list", kwargs={"issue_pk": self.issue_ticket.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_issue_comment(self):
        """
        Ensure a staff user can create a comment on an issue.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issuecomment-list", kwargs={"issue_pk": self.issue_ticket.pk}
        )
        data = {"content": "New comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_issue_comment(self):
        """
        Ensure a staff user can retrieve a comment.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issuecomment-detail",
            kwargs={"issue_pk": self.issue_ticket.pk, "pk": self.comment.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_issue_comment(self):
        """
        Ensure a staff user can update a comment.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issuecomment-detail",
            kwargs={"issue_pk": self.issue_ticket.pk, "pk": self.comment.pk},
        )
        data = {"content": "Updated comment"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Updated comment")

    def test_delete_issue_comment(self):
        """
        Ensure a staff user can delete a comment.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issuecomment-detail",
            kwargs={"issue_pk": self.issue_ticket.pk, "pk": self.comment.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ManagementIssueAttachmentViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.staff_user = create_user(
            email="staff@example.com", name="Staff User", is_cluster_staff=True
        )
        self.user.clusters.add(self.cluster)
        self.staff_user.clusters.add(self.cluster)
        self.issue_ticket = create_issue_ticket(self.cluster, self.user, self.staff_user)
        self.attachment = create_issue_attachment(self.issue_ticket, self.user)

    def test_list_issue_attachments(self):
        """
        Ensure attachments for an issue can be listed.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issueattachment-list",
            kwargs={"issue_pk": self.issue_ticket.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_issue_attachment(self):
        """
        Ensure a staff user can create an attachment for an issue.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issueattachment-list",
            kwargs={"issue_pk": self.issue_ticket.pk},
        )
        with open("test_attachment.txt", "w") as f:
            f.write("test content")
        with open("test_attachment.txt", "rb") as f:
            response = self.client.post(url, {"file": f}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_issue_attachment(self):
        """
        Ensure a staff user can retrieve an attachment.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issueattachment-detail",
            kwargs={"issue_pk": self.issue_ticket.pk, "pk": self.attachment.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_issue_attachment(self):
        """
        Ensure a staff user can delete an attachment.
        """
        self.client.force_authenticate(user=self.staff_user)
        url = reverse(
            "management:issueattachment-detail",
            kwargs={"issue_pk": self.issue_ticket.pk, "pk": self.attachment.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
