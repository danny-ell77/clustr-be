import copy
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AccountUser, UserVerification, Role, VerifyMode
from accounts.tests.test_serializers.test_members_import import IMPORT_DATA
from accounts.tests.utils import TestUsers, authenticate_user, MOCK_USER_PWD
from core.common.permissions import (
    AccessControlPermissions,
    AccountsPermissions,
    PaymentsPermissions,
)


class UserViewSetTestCase(TestUsers, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.staff = cls.create_cluster_staff()

    def setUp(self):
        super().setUp()
        authenticate_user(self.client, user=self.owner)

    def test_update_action(self):
        data = {
            "email_address": self.owner.email_address,
            "phone_number": self.owner.phone_number,
            "name": "Daniel Olah",
        }
        response = self.client.put(
            self.owner.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Daniel Olah")

    def test_owner_can_update_subuser_information(self):
        data = {
            "email_address": "new_email@example.com",
            "name": "New Name",
        }
        response = self.client.put(
            self.subuser.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "New Name")

    def test_owner_cannot_update_another_owners_or_subuser_information(self):
        other_owner = self.create_owner()
        new_data = {"name": "Unauthorized Change"}
        data = self._get_full_data(new_data, other_owner)
        response = self.client.put(
            other_owner.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_without_permissions_cannot_update_account_information(self):
        new_subuser = AccountUser.objects.create_subuser(
            self.owner, "subuser1@test.com", cluster=self.cluster, name="Valid Name"
        )
        authenticate_user(self.client, self.subuser)
        data = {"name": "Unauthorized Change"}

        response = self.client.put(
            new_subuser.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_without_permissions_cannot_update_account_information(self):
        authenticate_user(self.client, self.staff)
        data = {"name": "Unauthorized Change"}
        response = self.client.put(
            self.owner.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_with_permissions_can_update_member_account_information(self):
        perms = Permission.objects.filter(
            codename=AccountsPermissions.ManageAccountUser
        )
        new_subuser = AccountUser.objects.create_subuser(
            self.owner,
            "subuser2@test.com",
            cluster=self.cluster,
            name="Valid Name 2",
            permissions=perms,
        )

        authenticate_user(self.client, new_subuser)

        new_data = {"name": "Authorized Name Change"}
        data = self._get_full_data(new_data, self.subuser)

        response = self.client.put(
            self.subuser.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_with_permissions_can_modify_account_information(self):
        perms = Permission.objects.filter(codename=AccountsPermissions.ManageResidents)
        role = Role.objects.create(name="Resident Manager", owner=self.cluster_admin)
        role.permissions.set(perms)
        self.staff.groups.set([role])

        authenticate_user(self.client, self.staff)

        new_data = {"name": "Authorized Name Change"}
        data = self._get_full_data(new_data, self.owner)
        response = self.client.put(
            self.owner.get_absolute_url(), data=data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], new_data["name"])

    def test_admin_can_update_owners_information(self):
        authenticate_user(self.client, user=self.cluster_admin)
        new_data = {"name": "Admin Changed Name"}
        data = self._get_full_data(new_data, self.owner)
        response = self.client.put(
            self.owner.get_absolute_url(), data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Admin Changed Name")

    def test_owner_can_view_subuser_information(self):
        response = self.client.get(self.subuser.get_absolute_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], self.subuser.email_address)

    def test_list_action(self):
        response = self.client.get(
            reverse("user-list", kwargs={"version": settings.API_VERSION})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_from_auth_action(self):
        response = self.client.get(
            reverse("user-from_auth", kwargs={"version": settings.API_VERSION})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], self.owner.email_address)

    def test_permission_changes(self):
        perms = self.subuser.user_permissions.values_list("codename", flat=True)
        data = {"permissions": [*perms, PaymentsPermissions.ManageBill]}
        response = self.client.post(
            reverse(
                "user-change_permissions",
                kwargs={"version": settings.API_VERSION, "pk": self.subuser.pk},
            ),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.subuser.refresh_from_db()
        self.assertEqual(
            self.subuser.user_permissions.count(), len(data["permissions"])
        )

    def test_subuser_cannot_change_permissions(self):
        authenticate_user(self.client, user=self.subuser)
        data = {"permissions": [PaymentsPermissions.ManageBill]}
        response = self.client.post(
            reverse(
                "user-change_permissions",
                kwargs={"version": settings.API_VERSION, "pk": self.subuser.pk},
            ),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_email_verification(self, mock_email_sender):
        now = timezone.now()
        self.assertFalse(
            UserVerification.objects.filter(requested_at__gte=now).exists()
        )

        data = {"verify_mode": VerifyMode.TOKEN}
        response = self.client.post(
            reverse(
                "user-email_verification", kwargs={"version": settings.API_VERSION}
            ),
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserVerification.objects.filter(requested_at__gte=now).exists())
        mock_email_sender.assert_called()

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_password_change(self, mock_email_sender):
        self.assertTrue(self.owner.check_password(MOCK_USER_PWD))

        data = {"current_password": MOCK_USER_PWD, "new_password": "esoteric_new_pass"}
        response = self.client.post(
            reverse("user-change_password", kwargs={"version": settings.API_VERSION}),
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email_sender.assert_called()
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password("esoteric_new_pass"))

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_add_staff_action(self, mock_email_sender):
        role_ids = self.cluster_admin.roles.filter(
            permissions__codename__in=list(AccessControlPermissions)
        ).values_list("id", flat=True)
        data = {
            "email_address": "staff@example.com",
            "name": "Staff User",
            "roles": role_ids,
        }  # Assuming role IDs
        authenticate_user(self.client, self.cluster_admin)
        response = self.client.post(
            reverse("user-add_staff", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_email_sender.assert_called()

    @patch("core.common.email_sender.sender.AccountEmailSender.send")
    def test_add_subuser_action(self, mock_email_sender):
        data = {
            "email_address": "newuser@example.com",
            "name": "New User",
            "permissions": [
                AccountsPermissions.ManageAccountUser,
                *AccessControlPermissions,
            ],
        }
        response = self.client.post(
            reverse("user-add_user", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_email_sender.assert_called()

    @patch("core.common.email_sender.sender.AccountEmailSender.send_to_many")
    def test_member_import_action(self, mock_email_sender):
        now = timezone.now()
        user_q = AccountUser.objects.filter(cluster=self.cluster)
        old_user_count = user_q.count()

        data = copy.deepcopy(IMPORT_DATA)
        data["column_mapping"] = json.dumps(data["column_mapping"])

        authenticate_user(self.client, self.cluster_admin)
        response = self.client.post(
            reverse("user-import_members", kwargs={"version": settings.API_VERSION}),
            data=data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email_sender.assert_called()
        self.assertGreater(user_q.count(), old_user_count)
        self.assertEqual(
            UserVerification.objects.filter(requested_at__gte=now).count(),
            user_q.count() - old_user_count,
        )

    def test_get_import_template_action(self):
        authenticate_user(self.client, self.cluster_admin)

        response = self.client.get(
            f"{reverse('user-resident_import_template',kwargs={'version': settings.API_VERSION})}?format=1",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_approve_resident_action(self):
        self.assertFalse(self.subuser.approved_by_admin)
        authenticate_user(self.client, self.cluster_admin)
        response = self.client.post(
            reverse(
                "user-approve_account",
                kwargs={"version": settings.API_VERSION, "pk": self.subuser.pk},
            ),
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.subuser.refresh_from_db()
        self.assertTrue(self.subuser.approved_by_admin)

    @classmethod
    def create_cluster_staff(cls):
        return AccountUser.objects.create_staff(
            owner=cls.cluster_admin,
            email_address="staff1@cluster1.com",
            cluster=cls.cluster,
        )

    def create_owner(self):
        return AccountUser.objects.create_owner(
            email_address="user@test.com",
            password="testpass",
            cluster=self.cluster,
            name="Some User",
        )

    def _get_full_data(self, new_data, user: AccountUser):
        data = vars(user).copy()
        data.pop("_state")
        data.update(new_data)
        return data
