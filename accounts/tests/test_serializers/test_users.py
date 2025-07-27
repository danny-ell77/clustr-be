from typing import Type
from unittest.mock import patch

from django.http import HttpRequest
from django.test import TestCase

from accounts.models import AccountUser, Role
from accounts.serializers import (
    AccountSerializer,
    ClusterAdminAccountSerializer,
    OwnerAccountSerializer,
    StaffAccountSerializer,
    SubuserAccountSerializer,
)
from accounts.tests.utils import TestUsers, create_fake_request, create_mock_owner
from core.common.models import Cluster
from core.common.permissions import AccessControlPermissions


class BaseAccountSerializerTestCase:
    serializer_class: Type[AccountSerializer]
    valid_data: dict
    request: HttpRequest = HttpRequest()
    excluded_fields: list = []

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertDictEqual(serializer.errors, {})
        fields = {
            key for key in self.valid_data.keys() if key not in self.excluded_fields
        }
        self.assertTrue(set(serializer.validated_data.keys()).issuperset(fields))

        for key in fields:
            value = self.valid_data[key]
            expected = serializer.validated_data[key]
            with self.subTest(value=value, expected=expected):
                self.assertEqual(value, expected)

    def test_invalid_email_address(self):
        invalid_data = self.valid_data.copy()
        for invalid_attr in ["invalid_email", "", "invalidlength@test.com" * 50]:
            invalid_data["email_address"] = invalid_attr
            serializer = self.serializer_class(data=invalid_data)
            self.assertFalse(serializer.is_valid())
            self.assertIn("email_address", serializer.errors)
            self.assertDictEqual(serializer.validated_data, {})

    def test_invalid_name(self):
        invalid_data = self.valid_data.copy()
        for invalid_attr in ["", "Invalid Length" * 100]:
            invalid_data["name"] = invalid_attr
            serializer = self.serializer_class(data=invalid_data)
            self.assertFalse(serializer.is_valid())
            self.assertIn("name", serializer.errors)
            self.assertDictEqual(serializer.validated_data, {})

    def _create_instance(self) -> AccountUser:
        serializer = self.serializer_class(
            data=self.valid_data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class AccountOwnerSerializerTestCase(TestCase, BaseAccountSerializerTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.valid_data = {
            "email_address": "someuser@test.com",
            "name": "Jonny Lenn",
            "password": "mock123testify",
        }
        cls.serializer_class = OwnerAccountSerializer

    def test_invalid_password(self):
        invalid_data = self.valid_data.copy()
        invalid_data["password"] = "not_8"
        serializer = self.serializer_class(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        print(serializer.errors)
        self.assertIn("password", serializer.errors)
        self.assertDictEqual(serializer.validated_data, {})

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_create(self, mock_email_sender):
        instance = self._create_instance()
        self.assertIsInstance(instance, AccountUser)
        mock_email_sender.assert_called_once()

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_update(self, mock_email_sender):
        instance = self._create_instance()
        data = {"name": "New Name"}
        serializer = self.serializer_class(instance, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(instance.name, data["name"])


class SubuserAccountSerializerTestCase(TestCase, BaseAccountSerializerTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.valid_data = {
            "email_address": "subuser@test.com",
            "name": "Sarah Lenn",
            "permissions": [str(value) for value in AccessControlPermissions],
        }
        cls.serializer_class = SubuserAccountSerializer
        cls.excluded_fields = ["permissions"]
        cls.request = create_fake_request(owner=create_mock_owner())

    def test_permissions_field(self):
        serializer = self.serializer_class(data=self.valid_data)
        serializer.is_valid()
        self.assertIn("permissions", serializer.validated_data)

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_create(self, mock_email_sender):
        instance = self._create_instance()
        self.assertIsInstance(instance, AccountUser)
        mock_email_sender.assert_called()

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_update(self, mock_email_sender):
        instance = self._create_instance()
        data = {"name": "New Name"}
        serializer = self.serializer_class(instance, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(instance.name, data["name"])


class StaffAccountSerializerTestCase(
    TestUsers, TestCase, BaseAccountSerializerTestCase
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data = {
            "email_address": "staffuser@test.com",
            "name": "William Duke",
            "roles": Role.objects.filter(
                name=f"{cls.cluster_admin.pk}:Security"
            ).values_list("id", flat=True),
        }
        cls.serializer_class = StaffAccountSerializer
        cls.excluded_fields = ["roles"]
        cls.request = create_fake_request(owner=cls.cluster_admin)

    def test_roles_field(self):
        serializer = self.serializer_class(data=self.valid_data)
        serializer.is_valid()
        self.assertIn("groups", serializer.validated_data)

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_create(self, mock_email_sender):
        instance = self._create_instance()
        self.assertIsInstance(instance, AccountUser)
        mock_email_sender.assert_called()


class ClusterAdminAccountTestCase(TestUsers, TestCase):
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
        cls.serializer_class = ClusterAdminAccountSerializer
        cls.excluded_fields = ["roles"]
        cls.request = create_fake_request(owner=cls.cluster_admin)

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertIsInstance(serializer.validated_data, dict)
        self.assertDictEqual(serializer.errors, {})

    def test_invalid_data(self):
        invalid_cluster_data = {"name": "", "type": "invalid"}
        for key, value in invalid_cluster_data.items():
            data = self.valid_data.copy()
            data[key] = value
            serializer = self.serializer_class(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertDictEqual(serializer.validated_data, {})
            self.assertIn(key, serializer.errors)

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_create(self, mock_email_sender):
        serializer = self.serializer_class(data=self.valid_data)
        serializer.is_valid()
        instance = serializer.save()

        admin_data = self.valid_data.pop("admin")
        for key, value in self.valid_data.items():
            with self.subTest(key, expected=value):
                self.assertEqual(value, getattr(instance, key))

        admin_data.pop("password")
        self.assertIsInstance(instance, Cluster)
        user_set = AccountUser.objects.filter(**admin_data)
        self.assertTrue(user_set.exists())
        self.assertEqual(str(instance.owner_id), str(user_set.first().pk))
        mock_email_sender.assert_called_once()
