"""
Views for the members app.
"""

import logging
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from accounts.authentication_utils import (
    handle_user_login,
    handle_user_registration,
)
from accounts.models import (
    AccountUser,
    UserVerification,
    VerifyMode,
    VerifyReason,
)
from core.common.models.emergency import EmergencyContact
from accounts.models.sms_sender import SMSSender
from core.common.error_utils import log_exception_with_context, audit_log
from core.common.decorators import audit_viewset
from core.common.error_utils import exception_to_response_mapper
from core.common.responses import error_response
from core.common.exceptions import (
    AuthenticationException,
    ValidationException,
    ResourceNotFoundException,
)
from core.common.models import Cluster
from members.serializers import (
    MemberRegistrationSerializer,
    MemberLoginSerializer,
    MemberProfileSerializer,
    EmergencyContactSerializer,
    PhoneVerificationSerializer,
    VerifyPhoneSerializer,
)
from members.filters import EmergencyContactFilter

logger = logging.getLogger("clustr")


@audit_viewset(resource_type="user")
class MemberRegistrationView(generics.CreateAPIView):
    """
    API endpoint for member registration.
    """

    permission_classes = [AllowAny]
    serializer_class = MemberRegistrationSerializer

    @transaction.atomic
    @audit_log(event_type="user.register", resource_type="user")
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tokens = handle_user_registration(
                email_address=serializer.validated_data["email_address"],
                password=serializer.validated_data["password"],
                cluster_id=serializer.validated_data["cluster_id"],
                name=serializer.validated_data.get("name", ""),
                phone_number=serializer.validated_data.get("phone_number"),
                unit_address=serializer.validated_data.get("unit_address"),
                property_owner=serializer.validated_data.get("property_owner", False),
                request=request,
            )
            return Response(tokens, status=status.HTTP_201_CREATED)
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise


class MemberLoginView(APIView):
    """
    API endpoint for member login.
    """

    permission_classes = [AllowAny]
    serializer_class = MemberLoginSerializer

    @audit_log(event_type="user.login", resource_type="user")
    @exception_to_response_mapper(
        {
            AuthenticationException: lambda exc: error_response(
                "AUTHENTICATION_ERROR", str(exc), 401
            ),
            ValidationException: lambda exc: error_response(
                "VALIDATION_ERROR", str(exc), 400
            ),
            serializers.ValidationError: lambda exc: error_response(
                "VALIDATION_ERROR", str(exc.detail), 400
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tokens = handle_user_login(
                email_address=serializer.validated_data["email_address"],
                password=serializer.validated_data["password"],
                cluster_id=serializer.validated_data.get("cluster_id"),
                remember_me=serializer.validated_data.get("remember_me", False),
                device_name=serializer.validated_data.get("device_name"),
                device_id=serializer.validated_data.get("device_id"),
                request=request,
            )
            return Response(tokens)
        except AuthenticationException:
            raise
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise AuthenticationException(_("Login failed."))


class RequestPhoneVerificationView(APIView):
    """
    API endpoint to request phone verification.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PhoneVerificationSerializer

    @exception_to_response_mapper(
        {
            ValidationException: lambda exc: error_response(
                "VALIDATION_ERROR", str(exc), 400
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        user = request.user

        # Update user's phone number if different
        if user.phone_number != phone_number:
            user.phone_number = phone_number
            user.is_phone_verified = False
            user.save(update_fields=["phone_number", "is_phone_verified"])

        # Generate verification code
        verification = UserVerification.for_mode(
            VerifyMode.SMS, user, VerifyReason.PHONE_VERIFICATION
        )

        # Send SMS with verification code
        success = SMSSender.send_verification_code(phone_number, verification.otp)

        if success:
            return Response(
                {"detail": _("Verification code sent to your phone.")},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "detail": _(
                        "Failed to send verification code. Please try again later."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyPhoneView(APIView):
    """
    API endpoint to verify phone number with OTP.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = VerifyPhoneSerializer

    @exception_to_response_mapper(
        {
            ValidationException: lambda exc: error_response(
                "VALIDATION_ERROR", str(exc), 400
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        verification_code = serializer.validated_data["verification_code"]
        user = request.user

        # Check if phone number matches
        if user.phone_number != phone_number:
            raise ValidationException(_("Phone number does not match your account."))

        # Find verification record
        verification = UserVerification.objects.filter(
            otp=verification_code, requested_by=user, is_used=False
        ).first()

        if not verification or verification.is_expired:
            raise ValidationException(_("Invalid or expired verification code."))

        # Mark as verified
        with transaction.atomic():
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])
            verification.is_used = True
            verification.save(update_fields=["is_used"])

        return Response(
            {"detail": _("Phone number verified successfully.")},
            status=status.HTTP_200_OK,
        )


@audit_viewset(resource_type="user")
class MemberProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for member profile management.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MemberProfileSerializer

    def get_object(self):
        return self.request.user

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Handle emergency contacts if provided
        emergency_contacts_data = serializer.validated_data.pop(
            "emergency_contacts", None
        )

        # Update user profile
        self.perform_update(serializer)

        # Handle emergency contacts
        if emergency_contacts_data is not None:
            # Clear existing contacts and create new ones
            EmergencyContact.objects.filter(user=instance).delete()

            for contact_data in emergency_contacts_data:
                EmergencyContact.objects.create(user=instance, **contact_data)

        # Return updated profile
        return Response(self.get_serializer(instance).data)


@audit_viewset(resource_type="emergency_contact")
class EmergencyContactListView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating emergency contacts.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EmergencyContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmergencyContactFilter

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@audit_viewset(resource_type="emergency_contact")
class EmergencyContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating and deleting emergency contacts.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EmergencyContactSerializer

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)
