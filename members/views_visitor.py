"""
Views for visitor management in the members app.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from members.filters import MemberVisitorFilter, MemberVisitorLogFilter

from accounts.permissions import HasClusterPermission
from core.common.models import Visitor, VisitorLog
from core.common.permissions import AccessControlPermissions
from core.common.serializers.visitor_serializers import (
    VisitorSerializer,
    VisitorCreateSerializer,
    VisitorUpdateSerializer,
    VisitorLogSerializer,
    VisitorLogCreateSerializer,
)


class MemberVisitorViewSet(ModelViewSet):
    """
    ViewSet for managing visitors in the members app.
    Allows residents to view and manage their own visitors.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(AccessControlPermissions.ManageInvitation),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberVisitorFilter

    def get_queryset(self):
        """
        Return only visitors invited by the current user.
        """
        return Visitor.objects.filter(invited_by=self.request.user.id)

    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == "create":
            return VisitorCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return VisitorUpdateSerializer
        return VisitorSerializer

    def perform_create(self, serializer):
        """
        Create a new visitor and set the invited_by field to the current user.
        """
        serializer.save(invited_by=self.request.user.id)

    @action(
        detail=True,
        methods=["post"],
        url_path="revoke-invitation",
        url_name="revoke_invitation",
    )
    def revoke_invitation(self, request, pk=None):
        """
        Revoke a visitor invitation.
        """
        visitor = self.get_object()

        if visitor.status not in [
            Visitor.Status.CHECKED_IN,
            Visitor.Status.CHECKED_OUT,
        ]:
            visitor.status = Visitor.Status.REJECTED
            visitor.save()

            log_data = {
                "visitor": visitor.id,
                "log_type": VisitorLog.LogType.CANCELLED,
                "notes": request.data.get("notes", "Invitation revoked by resident"),
            }

            serializer = VisitorLogCreateSerializer(data=log_data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "invitation revoked"}, status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "error": "Cannot revoke invitation for a visitor who has already checked in"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class MemberVisitorLogViewSet(ModelViewSet):
    """
    ViewSet for managing visitor logs in the members app.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(AccessControlPermissions.ViewInvitation),
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberVisitorLogFilter
    serializer_class = VisitorLogSerializer

    def get_queryset(self):
        """
        Return only visitor logs for visitors invited by the current user.
        """
        visitor_ids = Visitor.objects.filter(
            invited_by=self.request.user.id
        ).values_list("id", flat=True)
        return VisitorLog.objects.filter(visitor_id__in=visitor_ids)
