from django.test import TestCase

from accounts.models import VerifyMode
from accounts.serializers import (
    AuthTokenPairSerializer,
    ForgotPasswordSerializer,
    PasswordChangeSerializer,
    ResetPasswordSerializer,
)
from accounts.tests.utils import TestUsers, create_fake_request, MOCK_USER_PWD


class AuthTokenPairSerializerTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_payload = {
            "email_address": cls.owner.email_address,
            "password": MOCK_USER_PWD,
        }
        cls.invalid_payload = {
            "invalid": "invalid",
        }
        cls.serializer_class = AuthTokenPairSerializer
        cls.request = create_fake_request(cls.owner)

    def test_valid_data(self):
        serializer = self.serializer_class(
            data=self.valid_payload, context={"request": self.request}
        )

        self.assertTrue(serializer.is_valid())
        self.assertDictEqual(serializer.errors, {})

    def test_invalid_data(self):
        serializer = self.serializer_class(
            data=self.invalid_payload, context={"request": self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.validated_data, {})

    def test_access_and_refresh_is_included_in_token(self):
        serializer = self.serializer_class(
            data=self.valid_payload, context={"request": self.request}
        )
        serializer.is_valid()
        self.assertIn("refresh", serializer.validated_data)
        self.assertIn("access", serializer.validated_data)


class ForgotPasswordSerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.serializer_class = ForgotPasswordSerializer
        cls.valid_data = {
            "email_address": "mock@mock.com",
            "verify_mode": VerifyMode.TOKEN,
        }
        cls.invalid_data = {"invalid": "invalid"}

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertIn("email_address", serializer.validated_data)
        self.assertIn("mode", serializer.validated_data)
        self.assertDictEqual(serializer.errors, {})

        email_missing = self.valid_data.copy()
        email_missing.pop("email_address")
        serializer = self.serializer_class(data=email_missing)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email_address", serializer.errors)
        self.assertDictEqual(serializer.validated_data, {})

    def test_invalid_data(self):
        serializer = self.serializer_class(data=self.invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.validated_data, {})
        self.assertTrue(serializer.errors)


class ResetPasswordSerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.serializer_class = ResetPasswordSerializer
        cls.valid_data = {
            "verification_key": "some_key",
            "password": "some_cool_password",
        }
        cls.invalid_data = {"invalid": "invalid"}

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertIn("verification_key", serializer.validated_data)
        self.assertIn("password", serializer.validated_data)
        self.assertDictEqual(serializer.errors, {})

        # Test for required fields
        for field in ["verification_key", "password"]:
            data = self.valid_data.copy()
            data.pop(field)
            serializer = self.serializer_class(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn(field, serializer.errors)
            self.assertDictEqual(serializer.validated_data, {})

    def test_invalid_data(self):
        serializer = self.serializer_class(data=self.invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.validated_data, {})
        self.assertTrue(serializer.errors)


class PasswordChangeSerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.serializer_class = PasswordChangeSerializer
        cls.valid_data = {
            "current_password": "current_password",
            "new_password": "new_password",
            "force_logout": True,
        }
        cls.invalid_data = {"invalid": "invalid"}

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        serializer.is_valid()
        print(serializer.errors)
        self.assertIn("current_password", serializer.validated_data)
        self.assertIn("new_password", serializer.validated_data)
        self.assertDictEqual(serializer.errors, {})

        for field in ["current_password", "new_password"]:
            data = self.valid_data.copy()
            data.pop(field)
            serializer = self.serializer_class(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn(field, serializer.errors)
            self.assertDictEqual(serializer.validated_data, {})

    def test_invalid_data(self):
        serializer = self.serializer_class(data=self.invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.validated_data, {})
        self.assertTrue(serializer.errors)
