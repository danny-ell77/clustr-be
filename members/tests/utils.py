"""
Utility functions for members app tests.
"""
from datetime import timedelta
from typing import Optional
from uuid import uuid4

from django.utils import timezone

from accounts.models import AccountUser
from accounts.utils import generate_strong_password
from core.common.models import (
    Cluster,
    Announcement,
    AnnouncementComment,
    AnnouncementLike,
    AnnouncementReadStatus,
    MaintenanceLog,
    MaintenanceType,
    MaintenancePriority,
    Visitor,
    Invitation,
)
from core.common.models.emergency import EmergencyContact, EmergencyContactType
from core.common.models.helpdesk import IssueTicket, IssueComment, IssueStatus


MOCK_USER_PWD = generate_strong_password()


def create_user(
    email="testmember@example.com",
    name="Test Member",
    phone_number="+2348000000001",
    is_cluster_admin=False,
    is_owner=True,
    cluster: Optional[Cluster] = None,
):
    """
    Create and return a member user.
    """
    user = AccountUser.objects.create_owner(
        email_address=email,
        password=MOCK_USER_PWD,
        name=name,
        phone_number=phone_number,
        is_cluster_admin=is_cluster_admin,
        is_owner=is_owner,
    )
    if cluster:
        user.clusters.add(cluster)
        user.primary_cluster = cluster
        user.save(update_fields=["primary_cluster"])
    return user


def create_cluster(name="Test Estate"):
    """
    Create and return a new cluster.
    """
    admin = AccountUser.objects.create_admin(
        f"admin-{uuid4().hex[:6]}@cluster.com", MOCK_USER_PWD, name="Cluster Admin"
    )
    cluster = Cluster.objects.create(
        type=Cluster.Types.ESTATE,
        name=name,
        address="123 Test Street",
        city="Test City",
        state="Test State",
        country="Nigeria",
        primary_contact_name="Admin Contact",
        primary_contact_email="contact@cluster.com",
        primary_contact_phone="+2348000000000",
    )
    admin.clusters.add(cluster)
    admin.primary_cluster = cluster
    admin.save()
    return cluster, admin


def authenticate_user(client, user: AccountUser):
    """
    Authenticate the user on the test client using JWT.
    Includes cluster_id in the token to enable middleware cluster context setting.
    """
    from accounts.authentication import generate_token

    cluster_id = str(user.primary_cluster.id) if user.primary_cluster else None
    tokens = generate_token(user, cluster_id=cluster_id)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")


def create_announcement(cluster, author, title="Test Announcement", content="Test Content", is_published=True):
    """
    Create and return a new announcement.
    """
    announcement = Announcement.objects.create(
        cluster=cluster,
        author_id=author.id,
        title=title,
        content=content,
        is_published=is_published,
        published_at=timezone.now() if is_published else None,
    )
    return announcement


def create_emergency_contact(user, name="Emergency Contact", phone="+2348000000099"):
    """
    Create and return an emergency contact.
    """
    return EmergencyContact.objects.create(
        user=user,
        name=name,
        phone_number=phone,
        contact_type=EmergencyContactType.FAMILY,
    )


def create_maintenance_log(cluster, user, title="Test Maintenance"):
    """
    Create and return a maintenance log.
    """
    return MaintenanceLog.objects.create(
        cluster=cluster,
        requested_by=user,
        title=title,
        description="A test maintenance request.",
        maintenance_type=MaintenanceType.GENERAL,
        priority=MaintenancePriority.MEDIUM,
    )


def create_issue_ticket(cluster, user, title="Test Issue"):
    """
    Create and return an issue ticket.
    """
    return IssueTicket.objects.create(
        cluster=cluster,
        reported_by=user,
        title=title,
        description="A test issue description.",
    )


def create_issue_comment(issue, author, content="Test comment"):
    """
    Create and return an issue comment.
    """
    return IssueComment.objects.create(
        issue=issue,
        author=author,
        content=content,
        cluster=issue.cluster,
    )


def create_visitor(user, name="Test Visitor", cluster=None):
    """
    Create and return a visitor.
    """
    from django.utils import timezone
    from uuid import uuid4

    if cluster is None:
        cluster = user.primary_cluster

    now = timezone.now()
    return Visitor.objects.create(
        cluster=cluster,
        invited_by=user.id,
        name=name,
        phone="+2348000000010",
        estimated_arrival=now + timedelta(hours=1),
        valid_date=now.date() + timedelta(days=1),
        access_code=uuid4().hex[:6].upper(),
        purpose="Visit",
    )


def create_invitation(user, title="Test Invitation", cluster=None):
    """
    Create and return an invitation.
    """
    from django.utils import timezone

    if cluster is None:
        cluster = user.primary_cluster

    visitor = create_visitor(user, cluster=cluster)
    now = timezone.now()
    return Invitation.objects.create(
        cluster=cluster,
        visitor=visitor,
        title=title,
        start_date=now.date(),
        end_date=now.date() + timedelta(days=7),
        created_by=user.id,
        status=Invitation.Status.ACTIVE,
    )

