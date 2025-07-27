"""
Members views for help desk system.
"""

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from members.filters import MembersIssueTicketFilter

from core.common.decorators import audit_viewset
from core.common.models.helpdesk import (
    IssueTicket,
    IssueComment,
    IssueAttachment,
    IssueStatus,
)
from core.common.serializers.helpdesk import (
    IssueTicketListSerializer,
    IssueTicketDetailSerializer,
    IssueTicketCreateSerializer,
    IssueCommentSerializer,
    IssueCommentCreateSerializer,
    IssueAttachmentSerializer,
    IssueAttachmentCreateSerializer,
)
from core.common.utils.file_storage import FileStorage


@audit_viewset(resource_type="issue_ticket")
class MembersIssueTicketViewSet(ModelViewSet):
    """
    Members viewset for issue tickets.
    Allows residents to create and view their own issues.
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MembersIssueTicketFilter

    def get_queryset(self):
        """Get issues reported by the current user with search functionality"""
        queryset = (
            IssueTicket.objects.filter(reported_by=self.request.user)
            .select_related("reported_by", "assigned_to", "cluster")
            .prefetch_related("comments", "attachments", "status_history")
        )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "list":
            return IssueTicketListSerializer
        elif self.action == "create":
            return IssueTicketCreateSerializer
        else:
            return IssueTicketDetailSerializer

    def list(self, request, *args, **kwargs):
        """List user's issues with filtering and search"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new issue ticket"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = serializer.save()

        # Return detailed view of created issue
        detail_serializer = IssueTicketDetailSerializer(
            issue, context={"request": request}
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Users can only update certain fields of their own issues"""
        instance = self.get_object()

        # Only allow updates if issue is not closed
        if instance.status == IssueStatus.CLOSED:
            return Response(
                {"error": "Cannot update closed issues"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Users can only update title and description
        allowed_fields = ["title", "description"]
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Users cannot delete issues, only staff can"""
        return Response(
            {"error": "You cannot delete issues"}, status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=False, methods=["get"])
    def my_statistics(self, request):
        """Get user's issue statistics"""
        queryset = self.get_queryset()

        stats = {
            "total_issues": queryset.count(),
            "open_issues": queryset.filter(
                status__in=[
                    IssueStatus.SUBMITTED,
                    IssueStatus.OPEN,
                    IssueStatus.IN_PROGRESS,
                    IssueStatus.PENDING,
                ]
            ).count(),
            "resolved_issues": queryset.filter(status=IssueStatus.RESOLVED).count(),
            "closed_issues": queryset.filter(status=IssueStatus.CLOSED).count(),
        }

        return Response(stats)


@audit_viewset(resource_type="issue_comment")
class MembersIssueCommentViewSet(ModelViewSet):
    """
    Members viewset for issue comments.
    Allows residents to comment on their own issues.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IssueCommentSerializer

    def get_queryset(self):
        """Get comments for issues reported by the current user"""
        issue_id = self.kwargs.get("issue_pk")

        # Verify the issue belongs to the current user
        try:
            issue = IssueTicket.objects.get(id=issue_id, reported_by=self.request.user)
        except IssueTicket.DoesNotExist:
            return IssueComment.objects.none()

        return (
            IssueComment.objects.filter(
                issue=issue, is_internal=False  # Users can't see internal comments
            )
            .select_related("author")
            .prefetch_related("attachments", "replies")
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return IssueCommentCreateSerializer
        return IssueCommentSerializer

    def get_serializer_context(self):
        """Add issue_id to serializer context"""
        context = super().get_serializer_context()
        context["issue_id"] = self.kwargs.get("issue_pk")
        return context

    def list(self, request, *args, **kwargs):
        """List comments for an issue"""
        # Only show top-level comments, replies are included in the serializer
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create a comment on an issue"""
        # Verify the issue belongs to the current user
        issue_id = self.kwargs.get("issue_pk")
        try:
            issue = IssueTicket.objects.get(id=issue_id, reported_by=self.request.user)
        except IssueTicket.DoesNotExist:
            return Response(
                {"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Users cannot create internal comments
        data = request.data.copy()
        data["is_internal"] = False

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Users can only update their own comments"""
        instance = self.get_object()

        if instance.author != request.user:
            return Response(
                {"error": "You can only edit your own comments"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Users can only delete their own comments"""
        instance = self.get_object()

        if instance.author != request.user:
            return Response(
                {"error": "You can only delete your own comments"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)


@audit_viewset(resource_type="issue_attachment")
class MembersIssueAttachmentViewSet(ModelViewSet):
    """
    Members viewset for issue attachments.
    Allows residents to upload attachments to their own issues.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IssueAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Get attachments for issues/comments by the current user"""
        issue_id = self.kwargs.get("issue_pk")
        comment_id = self.kwargs.get("comment_pk")

        # Verify the issue belongs to the current user
        try:
            issue = IssueTicket.objects.get(id=issue_id, reported_by=self.request.user)
        except IssueTicket.DoesNotExist:
            return IssueAttachment.objects.none()

        queryset = IssueAttachment.objects.filter()

        if comment_id:
            queryset = queryset.filter(comment_id=comment_id)
        else:
            queryset = queryset.filter(issue=issue)

        return queryset.select_related("uploaded_by")

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return IssueAttachmentCreateSerializer
        return IssueAttachmentSerializer

    def get_serializer_context(self):
        """Add issue_id and comment_id to serializer context"""
        context = super().get_serializer_context()
        context["issue_id"] = self.kwargs.get("issue_pk")
        context["comment_id"] = self.kwargs.get("comment_pk")
        return context

    def create(self, request, *args, **kwargs):
        """Upload and create attachment"""
        # Verify the issue belongs to the current user
        issue_id = self.kwargs.get("issue_pk")
        try:
            issue = IssueTicket.objects.get(id=issue_id, reported_by=self.request.user)
        except IssueTicket.DoesNotExist:
            return Response(
                {"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Upload file using FileStorage utility
        file_storage = FileStorage()
        file_url = file_storage.upload_file(file_obj, folder="helpdesk/attachments")

        # Create attachment record
        serializer_data = {
            "file_name": file_obj.name,
            "file_url": file_url,
            "file_size": file_obj.size,
            "file_type": file_obj.content_type,
        }

        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Users can only delete their own attachments"""
        instance = self.get_object()

        if instance.uploaded_by != request.user:
            return Response(
                {"error": "You can only delete your own attachments"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)
