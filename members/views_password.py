"""
Password management views for the members app.
"""

import logging
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from accounts.authentication_utils import check_account_lockout
from accounts.models import UserVerification, VerifyMode, VerifyReason
from accounts.serializers.auth import PasswordChangeSerializer
from accounts.utils import change_password
from core.common.error_utils import log_exception_with_context, audit_log
from core.common.exceptions import AuthenticationException, ValidationException

logger = logging.getLogger("clustr")


class ChangePasswordView(APIView):
    """
    API endpoint for changing password.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @audit_log(event_type="user.password_change", resource_type="user")
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        # Check if account is locked
        if check_account_lockout(user):
            raise AuthenticationException(
                _("Account is locked due to too many failed login attempts.")
            )

        try:
            # Change password
            change_password(
                user=user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
                force_logout=serializer.validated_data.get("force_logout", False),
                notify=settings.DEBUG,
            )

            return Response(
                {"detail": _("Password changed successfully.")},
                status=status.HTTP_200_OK,
            )
        except ValidationException:
            # Re-raise validation exceptions
            raise
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise ValidationException(_("Failed to change password."))


class RequestPasswordResetView(APIView):
    """
    API endpoint to request a password reset.
    """

    permission_classes = []  # Public endpoint

    @audit_log(event_type="user.password_reset_request", resource_type="user")
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        verify_mode = request.data.get("mode", VerifyMode.OTP)

        if not email:
            raise ValidationException(_("Email address is required."))

        # Always return success to prevent email enumeration attacks
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(email_address=email).first()
            if user:
                # Generate verification token/OTP
                verification = UserVerification.for_mode(
                    verify_mode, user, VerifyReason.PASSWORD_RESET
                )
                verification.send_mail()

                logger.info(
                    f"Password reset requested for: {email}",
                    extra={"user_id": str(user.id) if user else None},
                )
        except Exception as e:
            log_exception_with_context(e, request=request)
            # Still return success to prevent email enumeration

        return Response(
            {
                "detail": _(
                    "If an account exists with this email, a password reset link/code has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    API endpoint to reset password using a verification token/OTP.
    """

    permission_classes = []  # Public endpoint

    @audit_log(event_type="user.password_reset", resource_type="user")
    def post(self, request, *args, **kwargs):
        verification_key = request.data.get("verification_key")
        new_password = request.data.get("password")

        if not verification_key or not new_password:
            raise ValidationException(
                _("Verification key and new password are required.")
            )

        try:
            # Find verification record
            verification = self._get_verification(verification_key)

            if verification.is_expired:
                raise ValidationException(
                    _("Verification code has expired. Please request a new one.")
                )

            user = verification.requested_by

            # Change password
            with transaction.atomic():
                change_password(
                    user=user, new_password=new_password, force_logout=True, notify=True
                )

                # Mark verification as used
                verification.is_used = True
                verification.save(update_fields=["is_used"])

            logger.info(
                f"Password reset completed for: {user.email_address}",
                extra={"user_id": str(user.id)},
            )

            return Response(
                {"detail": _("Password has been reset successfully.")},
                status=status.HTTP_200_OK,
            )

        except ValidationException:
            # Re-raise validation exceptions
            raise
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise ValidationException(_("Failed to reset password."))

    def _get_verification(self, verification_key):
        """
        Get the verification record for the given key.

        Args:
            verification_key: The verification key (OTP or token)

        Returns:
            The verification record

        Raises:
            ValidationException: If the verification key is invalid
        """

        # Try to find by OTP first (for short keys)
        if len(verification_key) <= UserVerification.OTP_MAX_LENGTH:
            verification = UserVerification.objects.filter(
                otp=verification_key, is_used=False
            ).first()
        else:
            # For longer keys, try to unsign the token
            try:
                from django.core.signing import BadSignature
                from core.common.email_sender import NotificationTypes

                # Try to unsign the token
                token = UserVerification.unsign_token(
                    verification_key, reason=NotificationTypes.WEB_TOKEN_PASSWORD_RESET
                )

                verification = UserVerification.objects.filter(
                    token=token, is_used=False
                ).first()

            except BadSignature:
                # If unsigning fails, try direct match as fallback
                verification = UserVerification.objects.filter(
                    token=verification_key, is_used=False
                ).first()

        if not verification:
            raise ValidationException(_("Invalid verification key."))

        return verification
