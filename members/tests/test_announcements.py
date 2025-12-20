"""
Tests for member announcement views.
"""
import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models import AnnouncementLike, AnnouncementReadStatus
from .utils import create_cluster, create_user, create_announcement, authenticate_user


class MemberAnnouncementViewSetTests(APITestCase):
    """
    Test cases for MemberAnnouncementViewSet.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="announcement@example.com", cluster=self.cluster)
        self.announcement = create_announcement(self.cluster, self.admin)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list announcements.
        """
        url = reverse("members:announcement-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_authenticated(self):
        """
        Authenticated users should be able to list announcements.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_announcement(self):
        """
        Retrieving an announcement should increment view count and mark as read.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-detail", kwargs={"pk": str(self.announcement.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.announcement.id))
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.views_count, 1)
        self.assertTrue(AnnouncementReadStatus.objects.filter(
            announcement=self.announcement, user_id=self.member.id, is_read=True
        ).exists())

    def test_retrieve_nonexistent(self):
        """
        Retrieving a non-existent announcement should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:announcement-detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_like_announcement(self):
        """
        User should be able to like an announcement.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-like", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AnnouncementLike.objects.filter(
            announcement=self.announcement, user_id=self.member.id
        ).exists())
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.likes_count, 1)

    def test_like_already_liked(self):
        """
        Liking an already liked announcement should not error.
        """
        AnnouncementLike.objects.create(announcement=self.announcement, user_id=self.member.id)
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-like", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["liked"])

    def test_unlike_announcement(self):
        """
        User should be able to unlike an announcement.
        """
        AnnouncementLike.objects.create(announcement=self.announcement, user_id=self.member.id)
        self.announcement.likes_count = 1
        self.announcement.save()
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-unlike", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(AnnouncementLike.objects.filter(
            announcement=self.announcement, user_id=self.member.id
        ).exists())

    def test_unlike_not_liked(self):
        """
        Unliking an announcement that was not liked should return error.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-unlike", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unread_count(self):
        """
        User should be able to get unread announcements count.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-unread-count")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("unread_count", response.data)
        self.assertEqual(response.data["unread_count"], 1)

    def test_mark_as_read(self):
        """
        User should be able to mark an announcement as read.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-mark-as-read", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(AnnouncementReadStatus.objects.filter(
            announcement=self.announcement, user_id=self.member.id, is_read=True
        ).exists())

    def test_mark_as_unread(self):
        """
        User should be able to mark an announcement as unread.
        """
        AnnouncementReadStatus.objects.create(
            announcement=self.announcement, user_id=self.member.id, is_read=True
        )
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-mark-as-unread", kwargs={"pk": str(self.announcement.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_comments(self):
        """
        User should be able to get comments for an announcement.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-comments", kwargs={"pk": str(self.announcement.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_comment(self):
        """
        User should be able to add a comment to an announcement.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-add-comment", kwargs={"pk": str(self.announcement.id)})
        data = {"content": "This is a test comment."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_comment_empty_content(self):
        """
        Adding a comment with empty content should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-add-comment", kwargs={"pk": str(self.announcement.id)})
        data = {"content": ""}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_categories(self):
        """
        User should be able to get announcement categories.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-categories")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_attachments(self):
        """
        User should be able to get attachments for an announcement.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:announcement-attachments", kwargs={"pk": str(self.announcement.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
