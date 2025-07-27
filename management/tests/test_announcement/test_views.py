from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import (
    create_user,
    create_cluster,
    create_announcement,
    create_announcement_comment,
    create_announcement_attachment,
)


class ManagementAnnouncementViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.announcement = create_announcement(self.cluster, self.admin_user)

    def test_list_announcements_unauthenticated(self):
        """
        Ensure unauthenticated users cannot list announcements.
        """
        url = reverse("management:announcement-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_announcements_authenticated_no_permission(self):
        """
        Ensure users without permission cannot list announcements.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:announcement-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_announcements_authenticated_with_permission(self):
        """
        Ensure users with permission can list announcements.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_announcement_unauthenticated(self):
        """
        Ensure unauthenticated users cannot create announcements.
        """
        url = reverse("management:announcement-list")
        data = {"title": "New Announcement", "content": "Test content"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_announcement_authenticated_no_permission(self):
        """
        Ensure users without permission cannot create announcements.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:announcement-list")
        data = {"title": "New Announcement", "content": "Test content"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_announcement_authenticated_with_permission(self):
        """
        Ensure users with permission can create announcements.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-list")
        data = {"title": "New Announcement", "content": "Test content"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_announcement_unauthenticated(self):
        """
        Ensure unauthenticated users cannot retrieve an announcement.
        """
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_announcement_authenticated_no_permission(self):
        """
        Ensure users without permission cannot retrieve an announcement.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_announcement_authenticated_with_permission(self):
        """
        Ensure users with permission can retrieve an announcement.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_announcement_unauthenticated(self):
        """
        Ensure unauthenticated users cannot update an announcement.
        """
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        data = {"title": "Updated Title"}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_announcement_authenticated_no_permission(self):
        """
        Ensure users without permission cannot update an announcement.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        data = {"title": "Updated Title"}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_announcement_authenticated_with_permission(self):
        """
        Ensure users with permission can update an announcement.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        data = {"title": "Updated Title", "content": "Updated Content"}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.title, "Updated Title")

    def test_partial_update_announcement_authenticated_with_permission(self):
        """
        Ensure users with permission can partially update an announcement.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        data = {"title": "Partial Update"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.title, "Partial Update")

    def test_delete_announcement_unauthenticated(self):
        """
        Ensure unauthenticated users cannot delete an announcement.
        """
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_announcement_authenticated_no_permission(self):
        """
        Ensure users without permission cannot delete an announcement.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_announcement_authenticated_with_permission(self):
        """
        Ensure users with permission can delete an announcement.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-detail", kwargs={"pk": self.announcement.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_comments(self):
        """
        Ensure comments for an announcement can be retrieved.
        """
        create_announcement_comment(self.announcement, self.user)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-comments", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_add_comment(self):
        """
        Ensure a comment can be added to an announcement.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-add-comment", kwargs={"pk": self.announcement.pk})
        data = {"content": "A new comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_engagement_metrics(self):
        """
        Ensure engagement metrics for an announcement can be retrieved.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-engagement-metrics", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("views_count", response.data)
        self.assertIn("likes_count", response.data)
        self.assertIn("comments_count", response.data)

    def test_publish_announcement(self):
        """
        Ensure an announcement can be published.
        """
        self.announcement.is_published = False
        self.announcement.save()
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-publish", kwargs={"pk": self.announcement.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.announcement.refresh_from_db()
        self.assertTrue(self.announcement.is_published)

    def test_unpublish_announcement(self):
        """
        Ensure an announcement can be unpublished.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-unpublish", kwargs={"pk": self.announcement.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.announcement.refresh_from_db()
        self.assertFalse(self.announcement.is_published)

    def test_get_attachments(self):
        """
        Ensure attachments for an announcement can be retrieved.
        """
        create_announcement_attachment(self.announcement)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-attachments", kwargs={"pk": self.announcement.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_add_attachment(self):
        """
        Ensure an attachment can be added to an announcement.
        """
        attachment = create_announcement_attachment(self.announcement)
        attachment.announcement = None
        attachment.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-add-attachment", kwargs={"pk": self.announcement.pk})
        data = {"attachment_id": str(attachment.id)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_remove_attachment(self):
        """
        Ensure an attachment can be removed from an announcement.
        """
        attachment = create_announcement_attachment(self.announcement)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:announcement-remove-attachment", kwargs={"pk": self.announcement.pk})
        data = {"attachment_id": str(attachment.id)}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)