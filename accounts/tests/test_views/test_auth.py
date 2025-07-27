import secrets
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core.signing import Signer
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AccountUser, UserVerification, VerifyMode, VerifyReason
from accounts.tests.utils import TestUsers, MOCK_USER_PWD
from core.common.email_sender import NotificationTypes
from core.common.models import Cluster


class SignInViewTestCase(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_valid_login(self):
        self.assertTrue(self.owner.check_password(MOCK_USER_PWD))
        data = {
            "email_address": self.owner.email_address,
            "password": MOCK_USER_PWD,
        }
        response = self.client.post(
            reverse("login", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_invalid_login(self):
        data = {
            "email_address": "notfound@gmail.com",
            "password": "@!qwer45",
        }
        response = self.client.post(
            reverse("login", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_subuser_login(self):
        password = "skyfort123"
        self.subuser.set_password(password)
        self.subuser.save()
        data = {"email_address": self.subuser.email_address, "password": password}
        response = self.client.post(
            reverse("login", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_staff_login(self):
        password = "skyfort123"
        staff = AccountUser.objects.create_staff(
            self.cluster_admin, "staff1@cluster.com", name="Harry Ford"
        )
        staff.set_password(password)
        staff.save()
        data = {"email_address": staff.email_address, "password": password}
        response = self.client.post(
            reverse("login", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_refresh_token(self):
        self.assertTrue(self.owner.check_password(MOCK_USER_PWD))
        data = {
            "email_address": self.owner.email_address,
            "password": MOCK_USER_PWD,
        }
        response = self.client.post(
            reverse("login", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        token_response = self.client.post(
            reverse("token_refresh", kwargs={"version": settings.API_VERSION}),
            data=dict(response.data),
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)


class ClusterRegistrationAPIView(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data = {
            "admin": {
                "email_address": "staffuser@test.com",
                "name": "William Duke",
                "password": "test123*&^()",
            },
            "name": "Oakridge Industrial Estate",
            "description": "Oakridge Industrial Estate: Modern manufacturing "
            "hub with diverse facilities, ample parking, 24/7 security, "
            "eco-friendly design, and excellent transport links.",
            "type": Cluster.Types.ESTATE,
        }

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_create(self, mock_email_sender):
        response = self.client.post(
            reverse("register_cluster", kwargs={"version": settings.API_VERSION}),
            data=self.valid_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)
        mock_email_sender.assert_called()

    def test_validation_error_on_duplicate_cluster_name(self):
        data = self.valid_data.copy()
        data["name"] = self.cluster.name
        response = self.client.post(
            reverse("register_cluster", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "cluster with this Name already exists."
        )

    def test_validation_error_on_duplicate_email_address(self):
        data = self.valid_data.copy()
        data["admin"]["email_address"] = self.cluster_admin.email_address
        response = self.client.post(
            reverse("register_cluster", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "user with this email address already exists."
        )


class ForgotPasswordViewTestCase(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.valid_data = {
            "email_address": cls.owner.email_address,
        }

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_valid_request(self, mock_email_sender):
        for mode in VerifyMode:
            with self.subTest(mode):
                self.valid_data["mode"] = mode
                response = self.client.post(
                    reverse(
                        "forgot_password", kwargs={"version": settings.API_VERSION}
                    ),
                    data=self.valid_data,
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                verification_set = UserVerification.objects.filter(
                    requested_by=self.owner
                )
                self.assertTrue(verification_set.exists())
                self.assertTrue(getattr(verification_set.first(), mode.lower()))
                mock_email_sender.assert_called()

    def test_invalid_request__invalid_email_address(self):
        data = self.valid_data.copy()
        email_address = "nonexistent@test.com"
        data["email_address"] = email_address
        response = self.client.post(
            reverse("forgot_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            UserVerification.objects.filter(
                requested_by__email_address=email_address
            ).exists()
        )

    def test_invalid_request__invalid_mode(self):
        data = self.valid_data.copy()
        data["mode"] = "INVALID"
        response = self.client.post(
            reverse("forgot_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            UserVerification.objects.filter(requested_by=self.owner).exists()
        )


class ResetPasswordTestCase(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data = {}
        cls.otp = UserVerification.generate_otp(cls.owner, VerifyReason.PASSWORD_RESET)
        cls.web_token = UserVerification.generate_token(
            cls.owner, VerifyReason.PASSWORD_RESET
        )
        cls.new_password = "new_valid_password"

    def test_otp(self):
        data = {"verification_key": self.otp.otp, "password": self.new_password}
        response = self.client.post(
            reverse("reset_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.owner.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertTrue(self.owner.check_password(self.new_password))

    def test_web_token(self):
        data = {
            "verification_key": self.web_token.sign_token(
                NotificationTypes.WEB_TOKEN_PASSWORD_RESET
            ),
            "password": self.new_password,
        }
        response = self.client.post(
            reverse("reset_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.owner.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertTrue(self.owner.check_password(self.new_password))

    def test_bad_token_signature(self):
        web_token = UserVerification.generate_token(
            self.owner, VerifyReason.PASSWORD_RESET
        )
        web_token.token = "invalid_reset_password_token_for_testcase"
        web_token.save(update_fields=["token"])
        data = {
            "verification_key": web_token.sign_token("invalid_reason"),
            "password": self.new_password,
        }
        response = self.client.post(
            reverse("reset_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_existent_key(self):
        token = secrets.token_urlsafe(nbytes=96)
        signer = Signer(salt=NotificationTypes.WEB_TOKEN_PASSWORD_RESET)
        valid_non_existent_signed_token = signer.sign(token)

        data = {
            "verification_key": valid_non_existent_signed_token,
            "password": self.new_password,
        }
        response = self.client.post(
            reverse("reset_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @freeze_time(timezone.now() + UserVerification.VALIDITY_WINDOW + timedelta(hours=1))
    def test_expired_key(self):
        data = {
            "verification_key": self.otp.otp,
            "password": self.new_password,
        }
        response = self.client.post(
            reverse("reset_password", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
