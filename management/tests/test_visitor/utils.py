
from datetime import date, timedelta
from django.utils import timezone
from accounts.models import AccountUser
from core.common.models import Cluster, Visitor, VisitorLog


def create_user(
    email="testuser@example.com",
    name="Test User",
    is_staff=False,
    is_superuser=False,
    is_cluster_admin=False,
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


def create_visitor(cluster, invited_by):
    """
    Create and return a new visitor.
    """
    visitor = Visitor.objects.create(
        cluster=cluster,
        name="Test Visitor",
        phone="+1234567890",
        estimated_arrival=timezone.now(),
        invited_by=invited_by.id,
        valid_date=date.today() + timedelta(days=7),
    )
    return visitor


def create_visitor_log(visitor, log_type=VisitorLog.LogType.CHECKED_IN):
    """
    Create and return a new visitor log.
    """
    log = VisitorLog.objects.create(
        visitor=visitor,
        log_type=log_type,
        cluster=visitor.cluster,
    )
    return log
