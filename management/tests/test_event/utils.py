
from datetime import date, time
from accounts.models import AccountUser
from core.common.models import Cluster, Event, EventGuest


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


def create_event(cluster, created_by):
    """
    Create and return a new event.
    """
    event = Event.objects.create(
        cluster=cluster,
        title="Test Event",
        event_date=date.today(),
        event_time=time(18, 0),
        location="Test Location",
        created_by=created_by.id,
    )
    return event


def create_event_guest(event, invited_by):
    """
    Create and return a new event guest.
    """
    guest = EventGuest.objects.create(
        event=event,
        name="Test Guest",
        invited_by=invited_by.id,
        cluster=event.cluster,
    )
    return guest
