from django.test import TestCase
from rest_framework import serializers

from accounts.models import Role, PRIMARY_ROLE_NAME
from accounts.serializers import RoleSerializer
from accounts.tests.test_models.utils import create_mock_role
from accounts.tests.utils import TestUsers, create_fake_request
from core.common.permissions import DEFAULT_PERMISSIONS, AccessControlPermissions


class RoleSerializerTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_payload, cls.role = create_mock_role(
            owner=cls.cluster_admin, name="Test"
        )

        cls.invalid_payload = {
            "reason": True,
        }
        cls.serializer_class = RoleSerializer
        cls.request = create_fake_request(cls.cluster_admin)
        cls.admin_role = Role.objects.get(
            name__icontains="administrator", owner=cls.cluster_admin
        )

    def test_valid_serializer(self):
        data = self.valid_payload.copy()
        data["name"] = "test:Test name"
        serializer = self.serializer_class(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())
        self.assertDictEqual(serializer.errors, {})
        serializer.save()
        self.assertIsInstance(serializer.data, dict)

    def test_invalid_serializer(self):
        serializer = self.serializer_class(
            data=self.invalid_payload, context={"request": self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.validated_data, {})

    def test_empty_serializer(self):
        serializer = self.serializer_class()
        self.assertDictEqual(
            serializer.data, {"name": None, "description": "", "permissions": []}
        )

    def test_validate_none_data(self):
        data = None
        serializer = self.serializer_class(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(
            serializer.errors, {"non_field_errors": ["No data provided"]}
        )

    def test_list_serializer(self):
        serializer = self.serializer_class(
            Role.objects.filter(id=self.role.id), many=True
        )
        self.assertIsInstance(serializer.data, list)

    def test_detail_serializer(self):
        serializer = self.serializer_class(self.role, many=False)
        self.assertIsInstance(serializer.data, dict)

    def test_primary_user_role_is_readonly(self):
        serializer = self.serializer_class(
            data={"name": "Administrator"}, context={"request": self.request}
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)
            serializer.save()

        serializer = self.serializer_class(
            self.admin_role,
            {"description": "test"},
            context={"request": self.request},
            partial=True,
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)
            serializer.save()

    def test_role_name_field(self):
        field = "name"
        value = "Test"
        # To representation
        serializer = self.serializer_class(
            self.admin_role, context={"request": self.request}
        )
        self.assertEqual(serializer.data[field], PRIMARY_ROLE_NAME)

        # To internal value
        serializer = self.serializer_class(
            data={field: value}, context={"request": self.request}
        )
        serializer.is_valid()
        self.assertEqual(serializer.validated_data[field], value)

    def test_permissions_field(self):
        field = "permissions"
        value = {str(perm) for perm in AccessControlPermissions}

        # To representation
        serializer = self.serializer_class(
            self.admin_role, context={"request": self.request}
        )
        permissions = {str(perm) for perm in serializer.data[field]}
        self.assertSetEqual(
            permissions, {perm for perms in DEFAULT_PERMISSIONS for perm in perms}
        )

        # To internal value
        serializer = self.serializer_class(
            data={"name": "Test", field: value}, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        permissions = {str(perm.codename) for perm in serializer.validated_data[field]}
        self.assertSetEqual(permissions, value)

        # Test validation error on invalid permissions
        invalid_permissions = {"Test"}
        with self.assertRaises(serializers.ValidationError):
            serializer = self.serializer_class(
                data={field: value | invalid_permissions},
                context={"request": self.request},
            )
            serializer.is_valid(raise_exception=True)
