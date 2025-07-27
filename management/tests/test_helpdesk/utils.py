
from accounts.models import AccountUser
from core.common.models import (
    Cluster,
    IssueTicket,
    IssueComment,
    IssueAttachment,
    IssueType,
    IssuePriority,
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


def create_issue_ticket(cluster, reported_by, assigned_to=None):
    """
    Create and return a new issue ticket.
    """
    ticket = IssueTicket.objects.create(
        cluster=cluster,
        reported_by=reported_by,
        assigned_to=assigned_to,
        title="Test Issue",
        description="Test issue description",
        issue_type=IssueType.OTHER,
        priority=IssuePriority.MEDIUM,
    )
    return ticket


def create_issue_comment(issue, author):
    """
    Create and return a new issue comment.
    """
    comment = IssueComment.objects.create(
        issue=issue, author=author, content="Test comment", cluster=issue.cluster
    )
    return comment


def create_issue_attachment(issue, uploaded_by):
    """
    Create and return a new issue attachment.
    """
    attachment = IssueAttachment.objects.create(
        issue=issue,
        uploaded_by=uploaded_by,
        file_name="test_attachment.txt",
        file_url="http://example.com/test_attachment.txt",
        file_size=1024,
        file_type="text/plain",
        cluster=issue.cluster,
    )
    return attachment
