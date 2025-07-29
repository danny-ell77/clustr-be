"""
Emergency management views for members app.
"""

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.utils.translation import gettext_lazy as _

from accounts.permissions import HasSpecificPermission
from core.common.models.emergency import (
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
)
from core.common.serializers.emergency_serializers import (
    EmergencyContactSerializer,
    EmergencyContactCreateSerializer,
    EmergencyContactUpdateSerializer,
    SOSAlertSerializer,
    SOSAlertCreateSerializer,
    SOSAlertUpdateSerializer,
    EmergencyResponseSerializer,
    EmergencyTypeChoicesSerializer,
    EmergencyContactTypeChoicesSerializer,
    IncidentReportSerializer,
)
from core.common.utils.emergency_utils import EmergencyManager
from core.common.permissions import CommunicationsPermissions


class EmergencyContactViewSet(ModelViewSet):
    """
    ViewSet for managing personal emergency contacts.
    Members can manage their own emergency contacts.
    """

    serializer_class = EmergencyContactSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ViewEmergencyContacts),
    ]

    def get_queryset(self):
        """Get emergency contacts for the current user"""
        return EmergencyContact.objects.filter(
            user=self.request.user, contact_type=EmergencyContactType.PERSONAL
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return EmergencyContactCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return EmergencyContactUpdateSerializer
        return EmergencyContactSerializer

    def perform_create(self, serializer):
        """Create emergency contact for current user"""
        serializer.save(
            user=self.request.user,
            contact_type=EmergencyContactType.PERSONAL,
            created_by=self.request.user.id,
        )

    def perform_update(self, serializer):
        """Update emergency contact"""
        serializer.save(last_modified_by=self.request.user.id)

    @action(
        detail=False,
        methods=["get"],
        url_path="emergency-types",
        url_name="emergency_types",
    )
    def emergency_types(self, request):
        """Get available emergency types"""
        choices = [
            {"value": choice[0], "label": choice[1]} for choice in EmergencyType.choices
        ]
        serializer = EmergencyTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="contact-types",
        url_name="contact_types",
    )
    def contact_types(self, request):
        """Get available contact types"""
        # Members can only create personal contacts
        choices = [
            {"value": EmergencyContactType.PERSONAL, "label": "Personal Contact"}
        ]
        serializer = EmergencyContactTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)


class SOSAlertViewSet(ModelViewSet):
    """
    ViewSet for managing SOS alerts.
    Members can create and view their own alerts.
    """

    serializer_class = SOSAlertSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ViewEmergency),
    ]

    def get_queryset(self):
        """Get SOS alerts for the current user"""
        return SOSAlert.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return SOSAlertCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return SOSAlertUpdateSerializer
        return SOSAlertSerializer

    def perform_create(self, serializer):
        """Create SOS alert"""
        alert = EmergencyManager.create_sos_alert(
            user=self.request.user,
            emergency_type=serializer.validated_data["emergency_type"],
            description=serializer.validated_data.get("description", ""),
            location=serializer.validated_data.get("location", ""),
            priority=serializer.validated_data.get("priority", "high"),
        )

        if not alert:
            return Response(
                {"error": _("Failed to create SOS alert")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return alert

    def perform_update(self, serializer):
        """Update SOS alert"""
        serializer.save(last_modified_by=self.request.user.id)

    @action(detail=True, methods=["post"], url_path="cancel", url_name="cancel")
    def cancel(self, request, pk=None):
        """Cancel an SOS alert"""
        alert = self.get_object()

        # Only the user who created the alert can cancel it
        if alert.user != request.user:
            return Response(
                {"error": _("You can only cancel your own alerts")},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = request.data.get("reason", "Cancelled by user")

        if EmergencyManager.cancel_alert(alert, request.user, reason):
            return Response({"message": _("Alert cancelled successfully")})
        else:
            return Response(
                {"error": _("Failed to cancel alert")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="active", url_name="active")
    def active(self, request):
        """Get active alerts for the current user"""
        active_alerts = EmergencyManager.get_user_alerts(
            request.user, status__in=["active", "acknowledged", "responding"]
        )
        serializer = self.get_serializer(active_alerts, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="emergency-types",
        url_name="emergency_types",
    )
    def emergency_types(self, request):
        """Get available emergency types"""
        choices = [
            {"value": choice[0], "label": choice[1]} for choice in EmergencyType.choices
        ]
        serializer = EmergencyTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="responses", url_name="responses")
    def responses(self, request, pk=None):
        """Get responses for a specific alert"""
        alert = self.get_object()
        responses = EmergencyResponse.objects.filter(
            cluster=request.cluster_context, alert=alert
        ).order_by("-created_at")

        serializer = EmergencyResponseSerializer(responses, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="incident-report",
        url_name="incident_report",
    )
    def incident_report(self, request, pk=None):
        """Generate detailed incident report for user's own alert"""
        alert = self.get_object()

        # Ensure user can only access their own alerts
        if alert.user != request.user:
            return Response(
                {"error": _("You can only view reports for your own alerts")},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generate incident report
        report = EmergencyManager.generate_alert_incident_report(alert)

        serializer = IncidentReportSerializer(report)
        return Response(serializer.data)


class EmergencyResponseViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for viewing emergency responses.
    Members can only view responses to their own alerts.
    """

    serializer_class = EmergencyResponseSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ViewEmergency),
    ]

    def get_queryset(self):
        """Get emergency responses for the current user's alerts"""
        user_alerts = SOSAlert.objects.filter(user=self.request.user)

        return EmergencyResponse.objects.filter(alert__in=user_alerts)
