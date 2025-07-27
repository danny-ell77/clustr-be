
from datetime import timedelta
from django.utils import timezone
from accounts.models import AccountUser
from core.common.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementAttachment,
    AnnouncementLike,
    AnnouncementView,
    AnnouncementReadStatus,
    Cluster,
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


def create_announcement(cluster, author, title="Test Announcement", content="Test Content"):
    """
    Create and return a new announcement.
    """
    announcement = Announcement.objects.create(
        cluster=cluster,
        author_id=author.id,
        title=title,
        content=content,
        published_at=timezone.now(),
    )
    return announcement


def create_announcement_comment(announcement, author, content="Test Comment"):
    """
    Create and return a new announcement comment.
    """
    comment = AnnouncementComment.objects.create(
        announcement=announcement,
        author_id=author.id,
        content=content,
        cluster=announcement.cluster,
    )
    return comment


def create_announcement_attachment(announcement, file_name="test_attachment.txt"):
    """
    Create and return a new announcement attachment.
    """
    # all_permissions
    attachment = AnnouncementAttachment.objects.create(
        announcement=announcement,
        file_name=file_name,
        file_url=f"http://example.com/{file_name}",
        file_size=1024,
        file_type="text/plain",
        cluster=announcement.cluster,
    )
    return attachment


def create_announcement_like(announcement, user):
    """
    Create and return a new announcement like.
    """
    like = AnnouncementLike.objects.create(
        announcement=announcement, user_id=user.id, cluster=announcement.cluster
    )
    return like


def create_announcement_view(announcement, user):
    """
    Create and return a new announcement view.
    """
    view = AnnouncementView.objects.create(
        announcement=announcement, user_id=user.id, cluster=announcement.cluster
    )
    return view


def create_announcement_read_status(announcement, user, is_read=True):
    """
    Create and return a new announcement read status.
    """
    status = AnnouncementReadStatus.objects.create(
        announcement=announcement,
        user_id=user.id,
        is_read=is_read,
        cluster=announcement.cluster,
    )
    return status
