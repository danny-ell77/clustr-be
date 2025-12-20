"""
Tests for member helpdesk (issue ticket) views.
"""
import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models.helpdesk import IssueTicket, IssueStatus
from .utils import create_cluster, create_user, create_issue_ticket, create_issue_comment, authenticate_user


class MembersIssueTicketViewSetTests(APITestCase):
    """
    Test cases for MembersIssueTicketViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="helpdesk@example.com", cluster=self.cluster)
        self.issue = create_issue_ticket(self.cluster, self.member)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list issues.
        """
        url = reverse("members:members-issues-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_issues(self):
        """
        User should only see their own issues.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.issue.id))

    def test_list_does_not_show_other_users_issues(self):
        """
        User should not see issues of other users.
        """
        other_user = create_user(email="other@example.com", cluster=self.cluster)
        create_issue_ticket(self.cluster, other_user, title="Other's Issue")
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_issue(self):
        """
        User should be able to create an issue ticket.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-list")
        data = {
            "title": "New Issue",
            "description": "Description of the new issue.",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(IssueTicket.objects.filter(title="New Issue", reported_by=self.member).exists())

    def test_create_issue_missing_title(self):
        """
        Creating an issue without title should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-list")
        data = {"description": "Only description."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_own_issue(self):
        """
        User should be able to retrieve their own issue.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-detail", kwargs={"pk": str(self.issue.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.issue.id))

    def test_retrieve_other_users_issue(self):
        """
        User should not be able to retrieve other user's issue.
        """
        other_user = create_user(email="otherretrieve@example.com", cluster=self.cluster)
        other_issue = create_issue_ticket(self.cluster, other_user)
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-detail", kwargs={"pk": str(other_issue.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_issue(self):
        """
        Retrieving non-existent issue should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:members-issues-detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_issue_title(self):
        """
        User should be able to update issue title.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-detail", kwargs={"pk": str(self.issue.id)})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.title, "Updated Title")

    def test_update_closed_issue_fails(self):
        """
        Updating a closed issue should fail.
        """
        self.issue.status = IssueStatus.CLOSED
        self.issue.save()
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-detail", kwargs={"pk": str(self.issue.id)})
        data = {"title": "Cannot Update"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_issue_forbidden(self):
        """
        Users should not be able to delete issues.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-detail", kwargs={"pk": str(self.issue.id)})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_statistics(self):
        """
        User should be able to get their issue statistics.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issues-my-statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_issues", response.data)
        self.assertEqual(response.data["total_issues"], 1)


class MembersIssueCommentViewSetTests(APITestCase):
    """
    Test cases for MembersIssueCommentViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="issuecomment@example.com", cluster=self.cluster)
        self.issue = create_issue_ticket(self.cluster, self.member)

    def test_list_comments(self):
        """
        User should be able to list comments on their issue.
        """
        create_issue_comment(self.issue, self.member, content="Test comment")
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issue-comments-list", kwargs={"issue_pk": str(self.issue.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_comment(self):
        """
        User should be able to create a comment on their issue.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issue-comments-list", kwargs={"issue_pk": str(self.issue.id)})
        data = {"content": "A new comment."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_comment_on_other_users_issue_fails(self):
        """
        User should not be able to comment on other user's issue.
        """
        other_user = create_user(email="othercomment@example.com", cluster=self.cluster)
        other_issue = create_issue_ticket(self.cluster, other_user)
        authenticate_user(self.client, self.member)
        url = reverse("members:members-issue-comments-list", kwargs={"issue_pk": str(other_issue.id)})
        data = {"content": "Should not work."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
