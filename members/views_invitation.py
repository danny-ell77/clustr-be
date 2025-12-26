"""
Views for invitation management in the members app.
"""

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import HasClusterPermission
from core.common.models import Invitation
from core.common.permissions import AccessControlPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.invitation_serializers import (
    InvitationSerializer,
    InvitationCreateSerializer,
    InvitationUpdateSerializer,
    InvitationRevokeSerializer,
)


@audit_viewset(resource_type="invitation")
class MemberInvitationViewSet(ModelViewSet):
    """
    ViewSet for managing invitations in the members app.
    Allows residents to view and manage their own invitations.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission.check_permissions(for_view=[AccessControlPermissions.ManageInvitation]),
    ]

    def get_queryset(self):
        """
        Return only invitations created by the current user.
        """
        if getattr(self, "swagger_fake_view", False):
            return Invitation.objects.none()

        return Invitation.objects.filter(created_by=self.request.user.id)

    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == "create":
            return InvitationCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return InvitationUpdateSerializer
        elif self.action == "revoke":
            return InvitationRevokeSerializer
        return InvitationSerializer

    def perform_create(self, serializer):
        """
        Create a new invitation and set the created_by field to the current user.
        """
        serializer.save(created_by=self.request.user.id)

    @action(detail=True, methods=["post"], url_path="revoke", url_name="revoke")
    def revoke(self, request, pk=None):
        """
        Revoke an invitation.
        """
        invitation = self.get_object()

        if invitation.status == Invitation.Status.ACTIVE:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                invitation.status = Invitation.Status.REVOKED
                invitation.revoked_by = request.user.id
                invitation.revoked_at = timezone.now()
                invitation.revocation_reason = serializer.validated_data.get(
                    "revocation_reason", ""
                )
                invitation.save()

                return Response(
                    InvitationSerializer(invitation).data,
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"error": "Cannot revoke an invitation that is not active"},
            status=status.HTTP_400_BAD_REQUEST,
        )
