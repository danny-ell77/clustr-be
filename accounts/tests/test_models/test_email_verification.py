import secrets
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from accounts.models import UserVerification, VerifyMode, VerifyReason
from accounts.tests.test_models.utils import create_mock_email_verification
from accounts.tests.utils import TestUsers
from core.common.code_generator import CodeGenerator


class BaseEmailVerificationTestCaseMixin:
    MODE: str
    token: UserVerification
    valid_data: dict

    def test_model_is_created(self):
        self.assertIsInstance(self.token, UserVerification)

    def test_model_fields(self):
        self.assertEqual(
            self.token.notification_type, self.valid_data["notification_type"]
        )
        self.assertEqual(getattr(self.token, self.MODE), self.valid_data[self.MODE])
        self.assertEqual(self.token.requested_by, self.valid_data["requested_by"])
        self.assertFalse(self.token.is_used)

    def test_string_representation(self):
        self.assertEqual(str(self.token), self.valid_data[self.MODE])

    @freeze_time(timezone.now() + timedelta(hours=3))
    def test_is_expired(self):
        self.token.is_used = True
        self.token.save()
        self.assertTrue(self.token.is_expired)

    def test_mark_as_verified(self):
        self.token.is_used = False
        self.token.save()
        self.token.mark_as_verified()
        self.assertTrue(self.token.is_used)
        self.assertTrue(self.owner.is_verified)

    def test_for_mode(self):
        token = UserVerification.for_mode(
            VerifyMode[self.MODE.upper()],
            reason=VerifyReason.PASSWORD_RESET,
            user=self.owner,
        )
        self.assertIsInstance(token, UserVerification)
        self.assertIsNotNone(getattr(token, self.MODE))

    @patch("core.notifications.manager.NotificationManager.send")
    def test_send_mail(self, mock_send):
        self.token.send_mail()
        mock_send.assert_called_once()

    def test_opt_and_token_not_none_constraint(self):
        self.token.otp = None
        self.token.token = None
        with self.assertRaises(ValidationError):
            self.token.save()


class OTPEmailVerificationTestCase(
    TestUsers, TestCase, BaseEmailVerificationTestCaseMixin
):
    MODE = "otp"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data, cls.token = create_mock_email_verification(
            cls.owner,
            otp=CodeGenerator.generate_code(length=UserVerification.OTP_MAX_LENGTH),
        )

    def test_generate_otp(self):
        token = UserVerification.generate_otp(self.owner, VerifyReason.RESEND_TOKEN)
        self.assertIsInstance(token, UserVerification)
        self.assertIsNotNone(token.otp)


class WebTokenEmailVerificationTestcase(
    TestUsers, TestCase, BaseEmailVerificationTestCaseMixin
):
    MODE = "token"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data, cls.token = create_mock_email_verification(
            cls.owner, token=secrets.token_urlsafe(nbytes=96)
        )

    def test_generate_web_token(self):
        token = UserVerification.generate_token(self.owner, VerifyReason.RESEND_TOKEN)
        self.assertIsInstance(token, UserVerification)
        self.assertIsNotNone(token.token)
