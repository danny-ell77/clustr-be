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

from accounts.authentication import generate_token
from accounts.authentication_utils import (
    check_account_lockout,
    handle_failed_login,
    handle_successful_login,
    get_client_ip,
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

        # Extract cluster_id from validated data
        cluster_id = serializer.validated_data.pop("cluster_id")

        try:
            # Get the cluster
            cluster = Cluster.objects.get(id=cluster_id)

            # Create the user
            user = AccountUser.objects.create_owner(
                email_address=serializer.validated_data["email_address"],
                password=serializer.validated_data["password"],
                **{
                    k: v
                    for k, v in serializer.validated_data.items()
                    if k != "password"
                },
            )

            # Associate user with cluster
            user.clusters.add(cluster)
            user.primary_cluster = cluster

            # For backward compatibility
            user.estates.add(cluster)
            user.primary_estate = cluster

            user.save()

            # Generate verification token
            verification = UserVerification.for_mode(
                VerifyMode.OTP, user, VerifyReason.EMAIL_VERIFICATION
            )
            verification.send_mail()

            # Generate authentication tokens
            tokens = generate_token(user, str(cluster.id))

            # Log successful registration
            logger.info(
                f"User registered successfully: {user.email_address}",
                extra={
                    "user_id": str(user.id),
                    "cluster_id": str(cluster.id),
                    "ip_address": get_client_ip(request),
                },
            )

            return Response(tokens, status=status.HTTP_201_CREATED)

        except Cluster.DoesNotExist:
            raise ResourceNotFoundException(_("Cluster not found."))
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
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get user by email
        email = serializer.validated_data.get("email_address")

        try:
            user = AccountUser.objects.get(email_address=email)

            # Check if account is locked
            if check_account_lockout(user):
                raise AuthenticationException(
                    _("Account is locked due to too many failed login attempts.")
                )

            # Validate password
            if not user.check_password(serializer.validated_data.get("password")):
                # Handle failed login
                handle_failed_login(user)
                raise AuthenticationException(_("Invalid credentials."))

            # Handle successful login
            handle_successful_login(user, get_client_ip(request))

            # Get cluster context if provided
            cluster_id = serializer.validated_data.get("cluster_id")

            # If no cluster_id provided but user has a primary cluster, use that
            if not cluster_id and user.primary_cluster:
                cluster_id = str(user.primary_cluster.id)

            # Generate tokens
            tokens = generate_token(
                user,
                cluster_id,
                # Use longer expiry if remember_me is True
                expiry=(
                    settings.JWT_EXTENDED_TOKEN_LIFETIME
                    if serializer.validated_data.get("remember_me")
                    else None
                ),
            )

            # Log successful login
            logger.info(
                f"User logged in successfully: {user.email_address}",
                extra={
                    "user_id": str(user.id),
                    "cluster_id": cluster_id or "None",
                    "ip_address": get_client_ip(request),
                    "device_name": serializer.validated_data.get(
                        "device_name", "unknown"
                    ),
                    "device_id": serializer.validated_data.get("device_id", "unknown"),
                },
            )

            return Response(tokens)

        except AccountUser.DoesNotExist:
            # For security reasons, use the same error message as invalid password
            raise AuthenticationException(_("Invalid credentials."))
        except AuthenticationException:
            # Re-raise authentication exceptions
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
