
from accounts.models import AccountUser
from core.common.models import (
    Cluster,
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
)


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


def create_emergency_contact(cluster, user=None, contact_type=EmergencyContactType.PERSONAL):
    """
    Create and return a new emergency contact.
    """
    contact = EmergencyContact.objects.create(
        cluster=cluster,
        user=user,
        name="Test Contact",
        phone_number="+1234567890",
        contact_type=contact_type,
        emergency_types=[EmergencyType.HEALTH, EmergencyType.FIRE],
    )
    return contact


def create_sos_alert(cluster, user):
    """
    Create and return a new SOS alert.
    """
    alert = SOSAlert.objects.create(
        cluster=cluster,
        user=user,
        emergency_type=EmergencyType.HEALTH,
        location="Test Location",
    )
    return alert


def create_emergency_response(alert, responder):
    """
    Create and return a new emergency response.
    """
    response = EmergencyResponse.objects.create(
        alert=alert,
        responder=responder,
        response_type="acknowledged",
        cluster=alert.cluster,
    )
    return response
