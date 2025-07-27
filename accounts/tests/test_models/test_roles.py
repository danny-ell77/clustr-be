from django.conf import settings
from django.test import TestCase

from accounts.models import Role
from accounts.tests.test_models.utils import create_mock_role
from accounts.tests.utils import TestUsers
from core.common.permissions import DEFAULT_ROLES


class RoleModelTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data, cls.role = create_mock_role(
            owner=cls.cluster_admin, name="Test"
        )

    def test_model_fields(self):
        self.assertEqual(self.role.owner.pk, self.valid_data["owner"])
        self.assertEqual(
            self.role.name, f'{self.cluster_admin.pk}:{self.valid_data["name"]}'
        )
        self.assertEqual(self.role.description, self.valid_data["description"])
        self.assertEqual(self.role.created_by, self.valid_data["created_by"])

    def test_string_representation(self):
        cluster = self.cluster_admin.cluster
        self.assertEqual(
            str(self.role),
            f"Role: {self.role.name}; Admin: {self.role.owner.name}; Cluster: {cluster.name or ''}",
        )

    def test_get_absolute_url(self):
        self.assertURLEqual(
            f"/api/{settings.API_VERSION}/roles/{self.role.pk}/",
            self.role.get_absolute_url(),
        )

    def test_verbose_names(self):
        verbose_name = self.role._meta.verbose_name
        verbose_name_plural = self.role._meta.verbose_name_plural
        self.assertEqual(verbose_name, "role")
        self.assertEqual(verbose_name_plural, "roles")

    def test_display_name(self):
        self.assertEqual(self.role.display_name, self.valid_data["name"])

    def test_owners_pk_is_included_in_role_name(self):
        self.assertTrue(self.role.name.startswith(f"{self.role.owner.pk}:"))

    def test_create_default_roles(self):
        for name in DEFAULT_ROLES.keys():
            with self.subTest(name):
                self.assertTrue(
                    Role.objects.filter(name=f"{self.cluster_admin.pk}:{name}").exists()
                )
