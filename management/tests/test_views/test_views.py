
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import create_user, create_cluster, create_role, get_permission
from accounts.models import AccountUser


class UserListViewTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        self.user1 = create_user(email="user1@example.com", name="User One")
        self.user1.clusters.add(self.cluster)
        self.user2 = create_user(email="user2@example.com", name="User Two")
        self.user2.clusters.add(self.cluster)

    def test_list_users_authenticated_with_permission(self):
        """
        Ensure admin users can list users.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:user-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_create_user_authenticated_with_permission(self):
        """
        Ensure admin users can create users.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:user-list")
        data = {
            "email_address": "newuser@example.com",
            "name": "New User",
            "password": "testpassword",
            "user_type": "SUB_USER",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_users_unauthenticated(self):
        """
        Ensure unauthenticated users cannot list users.
        """
        url = reverse("management:user-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_no_permission(self):
        """
        Ensure users without permission cannot list users.
        """
        user = create_user(email="nopermission@example.com", name="No Permission")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:user-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_unauthenticated(self):
        """
        Ensure unauthenticated users cannot create users.
        """
        url = reverse("management:user-list")
        data = {
            "email_address": "newuser2@example.com",
            "name": "New User 2",
            "password": "testpassword",
            "user_type": "SUB_USER",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_user_no_permission(self):
        """
        Ensure users without permission cannot create users.
        """
        user = create_user(email="nopermission2@example.com", name="No Permission 2")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:user-list")
        data = {
            "email_address": "newuser3@example.com",
            "name": "New User 3",
            "password": "testpassword",
            "user_type": "SUB_USER",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserDetailViewTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        self.user_to_manage = create_user(email="manage@example.com", name="Manage User")
        self.user_to_manage.clusters.add(self.cluster)

    def test_retrieve_user_authenticated_with_permission(self):
        """
        Ensure admin users can retrieve user details.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user_authenticated_with_permission(self):
        """
        Ensure admin users can update user details.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_to_manage.refresh_from_db()
        self.assertEqual(self.user_to_manage.name, "Updated Name")

    def test_delete_user_authenticated_with_permission(self):
        """
        Ensure admin users can delete (deactivate) users.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user_to_manage.refresh_from_db()
        self.assertFalse(self.user_to_manage.is_active)

    def test_retrieve_user_unauthenticated(self):
        """
        Ensure unauthenticated users cannot retrieve user details.
        """
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_user_no_permission(self):
        """
        Ensure users without permission cannot retrieve user details.
        """
        user = create_user(email="nopermission@example.com", name="No Permission")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user_unauthenticated(self):
        """
        Ensure unauthenticated users cannot update user details.
        """
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_no_permission(self):
        """
        Ensure users without permission cannot update user details.
        """
        user = create_user(email="nopermission2@example.com", name="No Permission 2")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_user_unauthenticated(self):
        """
        Ensure unauthenticated users cannot delete users.
        """
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_user_no_permission(self):
        """
        Ensure users without permission cannot delete users.
        """
        user = create_user(email="nopermission3@example.com", name="No Permission 3")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:user-detail", kwargs={"pk": self.user_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoleListViewTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        self.role1 = create_role(self.admin_user, name="Role One")
        self.role2 = create_role(self.admin_user, name="Role Two")

    def test_list_roles_authenticated_with_permission(self):
        """
        Ensure admin users can list roles.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:role-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_create_role_authenticated_with_permission(self):
        """
        Ensure admin users can create roles.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:role-list")
        data = {"name": "New Role", "description": "A new role"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_roles_unauthenticated(self):
        """
        Ensure unauthenticated users cannot list roles.
        """
        url = reverse("management:role-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_roles_no_permission(self):
        """
        Ensure users without permission cannot list roles.
        """
        user = create_user(email="nopermission@example.com", name="No Permission")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:role-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_role_unauthenticated(self):
        """
        Ensure unauthenticated users cannot create roles.
        """
        url = reverse("management:role-list")
        data = {"name": "New Role 2", "description": "A new role 2"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_role_no_permission(self):
        """
        Ensure users without permission cannot create roles.
        """
        user = create_user(email="nopermission2@example.com", name="No Permission 2")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:role-list")
        data = {"name": "New Role 3", "description": "A new role 3"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoleDetailViewTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        self.role_to_manage = create_role(self.admin_user, name="Role To Manage")

    def test_retrieve_role_authenticated_with_permission(self):
        """
        Ensure admin users can retrieve role details.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_role_authenticated_with_permission(self):
        """
        Ensure admin users can update role details.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        data = {"name": "Updated Role Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.role_to_manage.refresh_from_db()
        self.assertEqual(self.role_to_manage.name, "Updated Role Name")

    def test_delete_role_authenticated_with_permission(self):
        """
        Ensure admin users can delete roles.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_retrieve_role_unauthenticated(self):
        """
        Ensure unauthenticated users cannot retrieve role details.
        """
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_role_no_permission(self):
        """
        Ensure users without permission cannot retrieve role details.
        """
        user = create_user(email="nopermission@example.com", name="No Permission")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_role_unauthenticated(self):
        """
        Ensure unauthenticated users cannot update role details.
        """
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_role_no_permission(self):
        """
        Ensure users without permission cannot update role details.
        """
        user = create_user(email="nopermission2@example.com", name="No Permission 2")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_role_unauthenticated(self):
        """
        Ensure unauthenticated users cannot delete roles.
        """
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_role_no_permission(self):
        """
        Ensure users without permission cannot delete roles.
        """
        user = create_user(email="nopermission3@example.com", name="No Permission 3")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:role-detail", kwargs={"pk": self.role_to_manage.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AssignRoleViewTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        self.user_to_assign = create_user(email="assign@example.com", name="Assign User")
        self.user_to_assign.clusters.add(self.cluster)
        self.role_to_assign = create_role(self.admin_user, name="Role To Assign")

    def test_assign_role_authenticated_with_permission(self):
        """
        Ensure admin users can assign roles to users.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:assign-role")
        data = {"user_id": str(self.user_to_assign.pk), "role_ids": [str(self.role_to_assign.pk)]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_to_assign.refresh_from_db()
        self.assertIn(self.role_to_assign, self.user_to_assign.groups.all())

    def test_assign_role_unauthenticated(self):
        """
        Ensure unauthenticated users cannot assign roles.
        """
        url = reverse("management:assign-role")
        data = {"user_id": str(self.user_to_assign.pk), "role_ids": [str(self.role_to_assign.pk)]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_assign_role_no_permission(self):
        """
        Ensure users without permission cannot assign roles.
        """
        user = create_user(email="nopermission@example.com", name="No Permission")
        user.clusters.add(self.cluster)
        self.client.force_authenticate(user=user)
        url = reverse("management:assign-role")
        data = {"user_id": str(self.user_to_assign.pk), "role_ids": [str(self.role_to_assign.pk)]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_role_invalid_user(self):
        """
        Ensure assigning roles to an invalid user returns an error.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:assign-role")
        data = {"user_id": "12345678-1234-5678-1234-567812345678", "role_ids": [str(self.role_to_assign.pk)]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_invalid_role(self):
        """
        Ensure assigning invalid roles returns an error.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:assign-role")
        data = {"user_id": str(self.user_to_assign.pk), "role_ids": ["12345678-1234-5678-1234-567812345678"]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
