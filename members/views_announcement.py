"""
Views for announcement access in the members app.
"""

from django.db import transaction, models
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from members.filters import MemberAnnouncementFilter

from accounts.permissions import HasClusterPermission
from core.common.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementLike,
    AnnouncementView,
    AnnouncementReadStatus,
    AnnouncementAttachment,
)
from core.common.permissions import CommunicationsPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.announcement_serializers import (
    AnnouncementSerializer,
    AnnouncementCommentSerializer,
    AnnouncementCommentCreateSerializer,
)
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager


@audit_viewset(resource_type="announcement")
class MemberAnnouncementViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for members to view announcements.
    Members can view, like, and comment on announcements but cannot create or modify them.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(CommunicationsPermissions.ViewAnnouncement),
    ]
    serializer_class = AnnouncementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MemberAnnouncementFilter
    search_fields = ["title", "content"]
    ordering_fields = ["published_at", "views_count", "likes_count"]
    ordering = ["-published_at"]

    def get_queryset(self):
        """
        Return published announcements for the current cluster with read status filtering.
        """
        now = timezone.now()

        # Only show published and non-expired announcements
        queryset = Announcement.objects.filter(is_published=True).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve an announcement and track the view.
        """
        announcement = self.get_object()

        # Track the view
        view_obj, created = AnnouncementView.objects.get_or_create(
            announcement=announcement, user_id=request.user.id
        )

        # Update view count if this is a new view
        if created:
            with transaction.atomic():
                announcement.views_count += 1
                announcement.save(update_fields=["views_count"])

        # Mark as read
        read_status, _ = AnnouncementReadStatus.objects.get_or_create(
            announcement=announcement, user_id=request.user.id
        )
        if not read_status.is_read:
            read_status.is_read = True
            read_status.read_at = timezone.now()
            read_status.save(update_fields=["is_read", "read_at"])

        serializer = self.get_serializer(announcement)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="like",
        url_name="like",
    )
    def like(self, request, pk=None):
        """
        Like an announcement.
        """
        announcement = self.get_object()

        like_obj, created = AnnouncementLike.objects.get_or_create(
            announcement=announcement, user_id=request.user.id
        )

        if created:
            # Update like count
            with transaction.atomic():
                announcement.likes_count += 1
                announcement.save(update_fields=["likes_count"])

            return Response(
                {"detail": "Announcement liked successfully.", "liked": True},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"detail": "You have already liked this announcement.", "liked": True},
                status=status.HTTP_200_OK,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="unlike",
        url_name="unlike",
    )
    def unlike(self, request, pk=None):
        """
        Unlike an announcement.
        """
        announcement = self.get_object()

        try:
            like_obj = AnnouncementLike.objects.get(
                announcement=announcement, user_id=request.user.id
            )

            with transaction.atomic():
                like_obj.delete()

                # Update like count
                announcement.likes_count = max(0, announcement.likes_count - 1)
                announcement.save(update_fields=["likes_count"])

            return Response(
                {"detail": "Announcement unliked successfully.", "liked": False},
                status=status.HTTP_200_OK,
            )
        except AnnouncementLike.DoesNotExist:
            return Response(
                {"detail": "You have not liked this announcement.", "liked": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=["get"],
        url_path="comments",
        url_name="comments",
    )
    def comments(self, request, pk=None):
        """
        Get comments for a specific announcement.
        """
        announcement = self.get_object()
        comments = AnnouncementComment.objects.filter(announcement=announcement)

        # Pagination
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = AnnouncementCommentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AnnouncementCommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="add-comment",
        url_name="add_comment",
    )
    def add_comment(self, request, pk=None):
        """
        Add a comment to an announcement.
        """
        announcement = self.get_object()
        serializer = AnnouncementCommentCreateSerializer(data=request.data)

        if serializer.is_valid():
            with transaction.atomic():
                comment = serializer.save(
                    announcement=announcement, author_id=request.user.id
                )

                # Update comments count
                announcement.comments_count += 1
                announcement.save(update_fields=["comments_count"])

                # Send notification to announcement author if different user
                if announcement.author_id != request.user.id:
                    try:
                        NotificationManager.send(
                            event=NotificationEvents.COMMENT_REPLY,
                            recipients=[announcement.author],
                            cluster=announcement.cluster,
                            context={
                                "announcement_title": announcement.title,
                                "comment_content": comment.content,
                                "commenter_name": request.user.name,
                            },
                        )
                    except Exception:
                        # Log the error but don't fail the comment creation
                        pass

            return Response(
                AnnouncementCommentSerializer(comment).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-as-read",
        url_name="mark_as_read",
    )
    def mark_as_read(self, request, pk=None):
        """
        Mark an announcement as read.
        """
        announcement = self.get_object()

        read_status, created = AnnouncementReadStatus.objects.get_or_create(
            announcement=announcement, user_id=request.user.id
        )

        if not read_status.is_read:
            read_status.is_read = True
            read_status.read_at = timezone.now()
            read_status.save(update_fields=["is_read", "read_at"])

        return Response(
            {"detail": "Announcement marked as read.", "is_read": True},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-as-unread",
        url_name="mark_as_unread",
    )
    def mark_as_unread(self, request, pk=None):
        """
        Mark an announcement as unread.
        """
        announcement = self.get_object()

        try:
            read_status = AnnouncementReadStatus.objects.get(
                announcement=announcement, user_id=request.user.id
            )
            read_status.is_read = False
            read_status.read_at = None
            read_status.save(update_fields=["is_read", "read_at"])

            return Response(
                {"detail": "Announcement marked as unread.", "is_read": False},
                status=status.HTTP_200_OK,
            )
        except AnnouncementReadStatus.DoesNotExist:
            return Response(
                {"detail": "Announcement is already unread.", "is_read": False},
                status=status.HTTP_200_OK,
            )

    @action(
        detail=False,
        methods=["get"],
        url_path="unread-count",
        url_name="unread_count",
    )
    def unread_count(self, request):
        """
        Get the count of unread announcements for the current user.
        """
        # Get all published, non-expired announcements
        now = timezone.now()
        all_announcements = Announcement.objects.filter(is_published=True).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

        # Get read announcements for the current user
        read_announcement_ids = AnnouncementReadStatus.objects.filter(
            user_id=request.user.id, is_read=True
        ).values_list("announcement_id", flat=True)

        # Calculate unread count
        unread_count = all_announcements.exclude(id__in=read_announcement_ids).count()

        return Response({"unread_count": unread_count})

    @action(
        detail=False,
        methods=["get"],
        url_path="categories",
        url_name="categories",
    )
    def categories(self, request):
        """
        Get available announcement categories.
        """
        from core.common.models import AnnouncementCategory

        categories = [
            {"value": choice[0], "label": choice[1]}
            for choice in AnnouncementCategory.choices
        ]

        return Response(categories)

    @action(
        detail=True,
        methods=["get"],
        url_path="attachments",
        url_name="attachments",
    )
    def attachments(self, request, pk=None):
        """
        Get attachments for a specific announcement.
        """
        announcement = self.get_object()
        attachments = AnnouncementAttachment.objects.filter(announcement=announcement)

        from core.common.serializers.announcement_serializers import (
            AnnouncementAttachmentSerializer,
        )

        serializer = AnnouncementAttachmentSerializer(attachments, many=True)
        return Response(serializer.data)
