
from accounts.models import AccountUser, Role
from core.common.models import Cluster
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def create_user(
    email="testuser@example.com",
    name="Test User",
    is_staff=False,
    is_superuser=False,
    is_cluster_admin=False,
    is_owner=False,
):
    """
    Create and return a new user.
    """
    user = AccountUser.objects.create_user(
        email_address=email,
        password="testpassword",
        name=name,
        is_staff=is_staff,
        is_superuser=is_superuser,
        is_cluster_admin=is_cluster_admin,
        is_owner=is_owner,
    )
    return user


def create_cluster(name="Test Cluster"):
    """
    Create and return a new cluster.
    """
    cluster = Cluster.objects.create(
        name=name,
        address="123 Test Street",
        city="Test City",
        state="Test State",
        country="Test Country",
        primary_contact_name="Test Contact",
        primary_contact_email="contact@testcluster.com",
        primary_contact_phone="1234567890",
    )
    return cluster


def create_role(owner, name="Test Role", permissions=None):
    """
    Create and return a new role.
    """
    role = Role.objects.create(owner=owner, name=name)
    if permissions:
        role.permissions.set(permissions)
    return role


def get_permission(codename):
    """
    Get a permission by its codename.
    """
    content_type = ContentType.objects.get_for_model(AccountUser)  # Or any other model
    permission, _ = Permission.objects.get_or_create(
        codename=codename, name=codename, content_type=content_type
    )
    return permission
