from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from accounts.models import PRIMARY_ROLE_NAME, AccountUser, PreviousPasswords
from accounts.tests.utils import TestUsers
from core.common.permissions import DEFAULT_ROLES, AccessControlPermissions


class AccountUserTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = AccountUser.objects.create_admin(
            "mockadmin@mock.com", "mock", name="Jack Admin"
        )
        cls.owner_data = {
            "email_address": "mockowner@mock.com",
            "password": "mock",
            "name": "John Doe",
        }
        cls.owner = AccountUser.objects.create_owner(
            cls.owner_data["email_address"],
            cls.owner_data["password"],
            cluster=cls.cluster,
            name=cls.owner_data["name"],
        )

        cls.staff_data = {
            "name": "Jack Staff",
            "email_address": "mocksecurity@mock.com",
        }
        cls.role_name = f"{cls.admin.id}:Security"
        cls.staff_user = AccountUser.objects.create_staff(
            owner=cls.admin,
            email_address=cls.staff_data["email_address"],
            cluster=cls.cluster,
            roles=cls.admin.roles.filter(name=cls.role_name),
            name=cls.staff_data["name"],
        )

        cls.subuser_data = {"name": "Jane Doe", "email_address": "mocksubuser@mock.com"}
        cls.subuser = AccountUser.objects.create_subuser(
            cls.owner,
            cls.subuser_data["email_address"],
            cluster=cls.cluster,
            permissions=Permission.objects.filter(
                codename__in=[perm for perm in AccessControlPermissions]
            ),
            name=cls.subuser_data["name"],
        )

    def test_model_is_created(self):
        self.assertIsInstance(self.owner, AccountUser)

    def test_model_fields(self):
        self.assertEqual(self.owner.name, self.owner_data["name"])
        self.assertEqual(self.owner.email_address, self.owner_data["email_address"])

    def test_string_representation(self):
        self.assertEqual(
            str(self.owner), f"{self.owner.name} @ {self.owner.cluster.name}"
        )
        self.assertEqual(
            str(self.subuser), f"{self.subuser.name} @ {self.subuser.cluster.name}"
        )

    def test_owner_has_all_permissions(self):
        perms = [
            f"accounts.{str(perm.value)}"
            for perm in DEFAULT_ROLES[PRIMARY_ROLE_NAME]["permissions"]
        ]
        self.assertTrue(self.owner.has_all_permissions(perms))

    def test_admin_role(self):
        admin_role = self.admin.groups.first()
        self.assertIsInstance(admin_role, Group)
        self.assertEqual(admin_role.name, f"{self.admin.id}:{PRIMARY_ROLE_NAME}")

        role_perms = set(admin_role.permissions.values_list("codename", flat=True))
        required_perms = {
            str(perm.value) for perm in DEFAULT_ROLES[PRIMARY_ROLE_NAME]["permissions"]
        }
        self.assertSetEqual(role_perms, required_perms)

    def test_create_staff_subuser__security(self):
        self.assertIsInstance(self.staff_user, AccountUser)

        for attr, value in self.staff_data.items():
            self.assertEqual(getattr(self.staff_user, attr), value)

        role_perms = set(
            Permission.objects.filter(
                group__name=self.role_name, group__user=self.staff_user
            ).values_list("codename", flat=True)
        )
        required_perms = {
            str(perm.value) for perm in DEFAULT_ROLES["Security"]["permissions"]
        }
        self.assertSetEqual(role_perms, required_perms)

    def test_create_member_subuser(self):
        self.assertIsInstance(self.subuser, AccountUser)

        for attr, value in self.subuser_data.items():
            self.assertEqual(getattr(self.subuser, attr), value)

        user_perms = set(
            self.subuser.user_permissions.values_list("codename", flat=True)
        )
        required_perms = {perm for perm in AccessControlPermissions}
        self.assertSetEqual(user_perms, required_perms)


class PreviousPasswordsTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.previous_passwords: PreviousPasswords = PreviousPasswords.objects.filter(
            user=cls.owner
        ).first()
        cls.previous_passwords.passwords = ["unhashed_test_password"]
        cls.previous_passwords.save()

    def test_model_fields(self):
        self.assertEqual(self.previous_passwords.user, self.owner)
        self.assertListEqual(
            self.previous_passwords.passwords, ["unhashed_test_password"]
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.previous_passwords),
            f"{self.previous_passwords.user.get_full_name()}'s previous passwords",
        )

    def test_verbose_names(self):
        verbose_name = self.previous_passwords._meta.verbose_name
        verbose_name_plural = self.previous_passwords._meta.verbose_name_plural
        self.assertEqual(verbose_name, "previous passwords")
        self.assertEqual(verbose_name_plural, "previous passwords")

    def test_user_previous_passwords(self):
        self.assertListEqual(self.subuser.previous_passwords.passwords, [])
