from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import PRIMARY_ROLE_NAME, AccountUser, Role
from accounts.tests.utils import TestUsers, authenticate_user
from accounts.views.roles import DEFAULT_DUPLICATE_DETAIL_MESSAGE
from core.common.exceptions import CommonAPIErrorCodes
from core.common.permissions import PaymentsPermissions


class RoleViewSetTestCase(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin1 = AccountUser.objects.create_admin(
            "admin1@test.com", "test", name="Test Admin 1"
        )
        cls.security_role1 = Role.objects.filter(name=f"{cls.admin1.pk}:Security")
        cls.staff1 = AccountUser.objects.create_staff(
            cls.admin1, "staff1@test.com", name="Test Staff 1", roles=cls.security_role1
        )
        cls.staff2 = AccountUser.objects.create_staff(
            cls.admin1, "staff2@test.com", name="Test Staff 2", roles=cls.security_role1
        )
        cls.admin2 = AccountUser.objects.create_admin(
            "admin2@test.com", "test", name="Test Admin 2"
        )
        cls.security_role2 = Role.objects.filter(name=f"{cls.admin2.pk}:Security")
        cls.staff3 = AccountUser.objects.create_staff(
            cls.admin2, "staff3@test.com", name="Test Staff 3", roles=cls.security_role2
        )
        cls.data = {
            "owner": cls.admin1.pk,
            "name": "Account Manager",
            "description": "Test description",
            "created_by": cls.admin1.pk,
            "permissions": [value for value in PaymentsPermissions],
        }

    def test_role_list_endpoint_status_and_response_data(self):
        authenticate_user(self.client, self.admin1)
        response = self.client.get(
            reverse("role-list", kwargs={"version": settings.API_VERSION})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.admin1.roles.count())

    def test_create(self):
        self.assertFalse(
            Role.objects.filter(name__icontains=self.data["name"]).exists()
        )

        authenticate_user(self.client, self.admin2)
        response = self.client.post(
            reverse("role-list", kwargs={"version": settings.API_VERSION}),
            data=self.data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        formatted_name = f"{self.admin2.pk}:{response.data['name']}"
        created_role = Role.objects.get(name=formatted_name)
        self.assertEqual(formatted_name, created_role.name)
        self.assertEqual(response.data["description"], created_role.description)

        perms = created_role.permissions.values_list("codename", flat=True)
        for perm in response.data["permissions"]:
            self.assertIn(perm, perms)

    def test_retrieve(self):
        data = self.data.copy()
        owner = AccountUser.objects.get(pk=data.pop("owner"))
        permissions = data.pop("permissions")
        role = Role.objects.create(owner=owner, **data)
        role.permissions.set(Permission.objects.filter(codename__in=permissions))

        authenticate_user(self.client, self.admin1)
        response = self.client.get(role.get_absolute_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        formatted_name = f"{self.admin1.pk}:{response.data['name']}"
        self.assertEqual(formatted_name, role.name)
        self.assertEqual(response.data["description"], role.description)

        perms = role.permissions.values_list("codename", flat=True)
        for perm in response.data["permissions"]:
            self.assertIn(perm, perms)

    def test_update(self):
        data = {"name": "Head Security", "description": "Head of Security"}

        authenticate_user(self.client, self.admin2)
        role = self.security_role2.first()
        response = self.client.put(role.get_absolute_url(), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["description"], data["description"])

        role.refresh_from_db()
        formatted_name = f"{self.admin2.pk}:{response.data['name']}"
        self.assertEqual(formatted_name, role.name)
        self.assertEqual(response.data["description"], role.description)

    def test_delete(self):
        data = self.data.copy()
        owner = AccountUser.objects.get(pk=data.pop("owner"))
        permissions = data.pop("permissions")
        role = Role.objects.create(owner=owner, **data)
        role.permissions.set(Permission.objects.filter(codename__in=permissions))

        authenticate_user(self.client, self.admin1)
        response = self.client.delete(role.get_absolute_url())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Role.objects.filter(pk=role.pk).exists())

    def test_cannot_delete_admin_role(self):
        authenticate_user(self.client, self.admin2)
        admin_role = self.admin2.roles.get(name__icontains=PRIMARY_ROLE_NAME)
        response = self.client.delete(admin_role.get_absolute_url())

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        self.assertTrue(Role.objects.filter(pk=admin_role.pk).exists())

    def test_staff_cannot_create_roles(self):
        data = {
            "name": "test",
            "description": "test description",
            "owner": self.admin1.pk,
        }
        authenticate_user(self.client, self.staff1)
        response = self.client.post(
            reverse("role-list", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertFalse(
            Role.objects.filter(name=f"{self.staff1.owner_id}:test").exists()
        )

    def test_admin_can_view_all_staff_roles(self):
        authenticate_user(self.client, self.admin2)
        response = self.client.get(
            reverse("role-list", kwargs={"version": settings.API_VERSION})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        roles = Role.objects.filter(owner_id=self.admin2.id).values_list(
            "id", flat=True
        )
        for role in response.data:
            self.assertIn(role["id"], roles)

    def test_admin_cannot_view_another_clusters_roles(self):
        authenticate_user(self.client, self.admin1)
        other_role = self.admin2.roles.first()
        response = self.client.get(other_role.get_absolute_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_cannot_view_another_clusters_roles(self):
        authenticate_user(self.client, self.staff2)
        other_role = self.admin2.roles.first()
        response = self.client.get(other_role.get_absolute_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_view_roles_within_cluster(self):
        authenticate_user(self.client, self.staff1)
        other_role = self.staff2.groups.first()
        response = self.client.get(
            reverse(
                "role-detail",
                kwargs={"version": settings.API_VERSION, "pk": other_role.pk},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_duplicate_roles_return_duplicate_error(self):
        data = self.data.copy()
        data["name"] = "Security"  # record with unique field already exists
        authenticate_user(self.client, self.admin1)

        response = self.client.post(
            reverse("role-list", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], DEFAULT_DUPLICATE_DETAIL_MESSAGE)
        self.assertEqual(response.data["code"], CommonAPIErrorCodes.DUPLICATE_ENTITY)

    def test_duplicate_update_on_roles_return_duplicate_error(self):
        data = self.data.copy()
        data.pop("owner")
        data.pop("permissions")
        owner = AccountUser.objects.get(pk=self.admin1.pk)
        Role.objects.create(owner=owner, **data)

        other_role = Role.objects.filter(
            ~Q(name__icontains=PRIMARY_ROLE_NAME), owner=owner
        ).last()

        authenticate_user(self.client, self.admin1)
        response = self.client.put(other_role.get_absolute_url(), data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], DEFAULT_DUPLICATE_DETAIL_MESSAGE)
        self.assertEqual(response.data["code"], CommonAPIErrorCodes.DUPLICATE_ENTITY)
