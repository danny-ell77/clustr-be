"""
Views for child security management in the members app.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from members.filters import MemberChildFilter
from django.utils import timezone

from accounts.permissions import HasClusterPermission
from core.common.models import Child, ExitRequest, EntryExitLog
from core.common.permissions import AccessControlPermissions
from core.common.serializers.child_serializers import (
    ChildSerializer,
    ChildCreateSerializer,
    ChildUpdateSerializer,
    ExitRequestSerializer,
    ExitRequestCreateSerializer,
    ExitRequestUpdateSerializer,
    EntryExitLogSerializer,
)
from core.common.includes.file_storage import FileStorage


class MemberChildViewSet(ModelViewSet):
    """
    ViewSet for managing children in the members app.
    Allows residents to view and manage their own children.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageInvitation]),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberChildFilter

    def get_queryset(self):
        """
        Return only children belonging to the current user.
        """
        return Child.objects.filter(parent=self.request.user)

    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == "create":
            return ChildCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ChildUpdateSerializer
        return ChildSerializer

    def perform_create(self, serializer):
        """
        Create a new child and set the parent field to the current user.
        """
        serializer.save(parent=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-photo",
        url_name="upload_photo",
    )
    def upload_photo(self, request, pk=None):
        """
        Upload a profile photo for the child.
        """
        child = self.get_object()

        if "photo" not in request.FILES:
            return Response(
                {"error": "No photo file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        photo_file = request.FILES["photo"]

        try:
            # Upload the file using the file storage utility
            photo_url = FileStorage.upload_file(
                photo_file,
                folder="child_profiles",
                cluster_id=(
                    str(request.cluster_context.id)
                    if hasattr(request, "cluster_context")
                    else None
                ),
            )

            # Update the child's profile photo
            child.profile_photo = photo_url
            child.save(update_fields=["profile_photo"])

            return Response({"profile_photo": photo_url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to upload photo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MemberExitRequestViewSet(ModelViewSet):
    """
    ViewSet for managing exit requests in the members app.
    Allows residents to create and manage exit requests for their children.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageInvitation]),
    ]

    def get_queryset(self):
        """
        Return only exit requests for children belonging to the current user.
        """
        child_ids = Child.objects.filter(parent=self.request.user).values_list(
            "id", flat=True
        )
        return ExitRequest.objects.filter(child_id__in=child_ids)

    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == "create":
            return ExitRequestCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ExitRequestUpdateSerializer
        return ExitRequestSerializer

    def perform_create(self, serializer):
        """
        Create a new exit request and set the requested_by field to the current user.
        """
        # Validate that the child belongs to the current user
        child = serializer.validated_data["child"]
        if child.parent != self.request.user:
            raise permissions.PermissionDenied(
                "You can only create exit requests for your own children."
            )

        # Set default expiration time if not provided (24 hours from now)
        if "expires_at" not in serializer.validated_data:
            serializer.validated_data["expires_at"] = (
                timezone.now() + timezone.timedelta(hours=24)
            )

        serializer.save(requested_by=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        url_name="cancel",
    )
    def cancel(self, request, pk=None):
        """
        Cancel an exit request.
        """
        exit_request = self.get_object()

        # Only allow cancellation if the request is still pending
        if exit_request.status == ExitRequest.Status.PENDING:
            exit_request.status = ExitRequest.Status.DENIED
            exit_request.denied_by = request.user
            exit_request.denied_at = timezone.now()
            exit_request.denial_reason = "Cancelled by parent"
            exit_request.save()

            return Response(
                {"status": "exit request cancelled"}, status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Cannot cancel a request that is not pending"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class MemberEntryExitLogViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for viewing entry/exit logs in the members app.
    Allows residents to view logs for their own children.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ViewInvitation]),
    ]
    serializer_class = EntryExitLogSerializer

    def get_queryset(self):
        """
        Return only entry/exit logs for children belonging to the current user.
        """
        child_ids = Child.objects.filter(parent=self.request.user).values_list(
            "id", flat=True
        )
        return EntryExitLog.objects.filter(child_id__in=child_ids)

    @action(detail=False, methods=["get"], url_path="overdue", url_name="overdue")
    def overdue(self, request):
        """
        Get all overdue children for the current user.
        """
        child_ids = Child.objects.filter(parent=self.request.user).values_list(
            "id", flat=True
        )
        overdue_logs = EntryExitLog.objects.filter(
            child_id__in=child_ids, status=EntryExitLog.Status.OVERDUE
        )

        serializer = self.get_serializer(overdue_logs, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="active-exits",
        url_name="active_exits",
    )
    def active_exits(self, request):
        """
        Get all active exits (children currently out) for the current user.
        """
        child_ids = Child.objects.filter(parent=self.request.user).values_list(
            "id", flat=True
        )
        active_exits = EntryExitLog.objects.filter(
            child_id__in=child_ids,
            log_type=EntryExitLog.LogType.EXIT,
            status=EntryExitLog.Status.IN_PROGRESS,
        )

        serializer = self.get_serializer(active_exits, many=True)
        return Response(serializer.data)
