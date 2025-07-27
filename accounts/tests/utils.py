from typing import Optional

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import AccountUser
from accounts.utils import generate_strong_password
from core.common.models import Cluster


MOCK_USER_PWD = generate_strong_password()


def create_mock_cluster_admin() -> AccountUser:
    return AccountUser.objects.create_admin("mock@mock.com", MOCK_USER_PWD)


def create_mock_owner(cluster: Optional[Cluster] = None) -> AccountUser:
    return AccountUser.objects.create_owner(
        "mock2@mock.com", MOCK_USER_PWD, cluster=cluster
    )


def create_mock_subuser(owner: AccountUser, cluster: Cluster) -> AccountUser:
    return AccountUser.objects.create_subuser(owner, "mock3@mock.com", cluster=cluster)


def create_mock_cluster(admin: AccountUser) -> Cluster:
    return Cluster.objects.create(
        type=Cluster.Types.ESTATE, name="mock", owner_id=admin.pk
    )


class TestUsers:
    @classmethod
    def setUpTestData(cls):
        cls.cluster_admin = create_mock_cluster_admin()
        cls.cluster = create_mock_cluster(cls.cluster_admin)
        cls.cluster_admin.cluster = cls.cluster
        cls.cluster_admin.save(update_fields=["cluster"])
        cls.owner = create_mock_owner(cls.cluster)
        cls.subuser = create_mock_subuser(cls.owner, cls.cluster)


def authenticate_user(client, user: AccountUser):
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")


def create_fake_request(owner: AccountUser, **kwargs) -> Request:
    """get request with  user"""
    request = APIRequestFactory().get("/", **kwargs)
    request.user = owner
    return request
