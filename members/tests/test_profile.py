"""
Tests for member profile views.
"""
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from .utils import create_cluster, create_user, authenticate_user


class MemberProfileViewTests(APITestCase):
    """
    Test cases for MemberProfileView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="profile@example.com", cluster=self.cluster)

    def test_get_profile_unauthenticated(self):
        """
        Unauthenticated users should not be able to access the profile endpoint.
        """
        url = reverse("members:profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authenticated(self):
        """
        Authenticated users should be able to retrieve their profile.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], self.member.email_address)
        self.assertEqual(response.data["name"], self.member.name)

    def test_update_profile_name(self):
        """
        Users should be able to update their name.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:profile")
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, "Updated Name")

    def test_update_profile_unit_address(self):
        """
        Users should be able to update their unit address.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:profile")
        data = {"unit_address": "New Unit 202, Block B"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.unit_address, "New Unit 202, Block B")

    def test_update_profile_read_only_fields_ignored(self):
        """
        Read-only fields like email_address should not be updated.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:profile")
        original_email = self.member.email_address
        data = {"email_address": "hacked@example.com", "name": "Valid Update"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.email_address, original_email)
        self.assertEqual(self.member.name, "Valid Update")

    def test_update_profile_empty_body(self):
        """
        Updating with an empty body should not throw errors.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:profile")
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfilePictureUploadViewTests(APITestCase):
    """
    Test cases for ProfilePictureUploadView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="picture@example.com", cluster=self.cluster)

    def test_upload_picture_unauthenticated(self):
        """
        Unauthenticated users should not be able to upload a picture.
        """
        url = reverse("members:upload_profile_picture")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_picture_no_file(self):
        """
        Request without a file should return an error.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:upload_profile_picture")
        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_picture_invalid_file_type(self):
        """
        Uploading an invalid file type should return an error.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:upload_profile_picture")
        text_file = SimpleUploadedFile("test.txt", b"some text content", content_type="text/plain")
        response = self.client.post(url, {"file": text_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("members.views_profile.ProfilePictureUploadView._upload_to_storage")
    def test_upload_picture_valid_image(self, mock_upload):
        """
        Uploading a valid image should succeed.
        """
        mock_url = "https://storage.clustr.app/profile_pictures/test.gif"
        mock_upload.return_value = mock_url
        authenticate_user(self.client, self.member)
        url = reverse("members:upload_profile_picture")
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9'
            b'\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02\x44\x01\x00\x3b'
        )
        uploaded_file = SimpleUploadedFile("test.gif", small_gif, content_type="image/gif")
        response = self.client.post(url, {"file": uploaded_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], mock_url)
        self.member.refresh_from_db()
        self.assertEqual(self.member.profile_image_url, mock_url)


class ProfileUpdateVerificationViewTests(APITestCase):
    """
    Test cases for profile update verification flow.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="verify@example.com", cluster=self.cluster)

    def test_request_verification_unauthenticated(self):
        """
        Unauthenticated users should not be able to request verification.
        """
        url = reverse("members:request_profile_update_verification")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.models.email_verification.UserVerification.send_mail")
    def test_request_verification_success(self, mock_send_mail):
        """
        Authenticated users should be able to request verification.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:request_profile_update_verification")
        response = self.client.post(url, {"mode": "OTP"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()

    def test_verify_profile_update_missing_key(self):
        """
        Verification should fail if verification_key is missing.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_profile_update")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_profile_update_invalid_key(self):
        """
        Verification should fail with an invalid verification key.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:verify_profile_update")
        response = self.client.post(url, {"verification_key": "invalid"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
