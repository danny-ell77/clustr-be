import secrets
from datetime import timedelta
from typing import TYPE_CHECKING, Callable, Optional

from django.core.exceptions import ValidationError
from django.core.signing import Signer
from django.db import models, transaction
from django.db.models import TextChoices
from django.template import Context
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.common.code_generator import CodeGenerator
from core.common.email_sender import AccountEmailSender
from core.common.email_sender.types import NotificationTypes
from core.common.models import UUIDPrimaryKey

if TYPE_CHECKING:
    from accounts.models import AccountUser


class BaseUserToken:
    token: Optional[str]

    def sign_token(self, reason: str) -> Optional[str]:
        """
        Cryptographically signs the  token to help detect any sort of tampering when it is sent back to us
        by the client.
        """
        signer = Signer(salt=reason)
        if not self.token:
            return
        token = signer.sign(self.token)
        return token

    @classmethod
    def unsign_token(cls, signed_token: str, reason: str) -> str:
        """
        Unsigns the token. This could raise BadSignature exception if the token was tampered with.
        """
        signer = Signer(salt=reason)
        token = signer.unsign(signed_token)
        return token


class VerifyReason(TextChoices):
    PASSWORD_RESET = "PASSWORD_RESET", "Used for the forgot password flow"
    ONBOARDING = "ONBOARDING", "Used to onboard the user when first signing up"
    RESEND_TOKEN = "RESEND_TOKEN", "Used for re-sending verification tokens"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Used to verify user's email address"
    PHONE_VERIFICATION = "PHONE_VERIFICATION", "Used to verify user's phone number"
    PROFILE_UPDATE = "PROFILE_UPDATE", "Used when updating critical profile information"


class VerifyMode(TextChoices):
    OTP = "OTP"
    TOKEN = "TOKEN"
    SMS = "SMS"  # New mode for SMS verification


otp_notification_types = {
    VerifyReason.ONBOARDING: NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET,
    VerifyReason.PASSWORD_RESET: NotificationTypes.OTP_PASSWORD_RESET,
    VerifyReason.RESEND_TOKEN: NotificationTypes.RESEND_OTP,
    VerifyReason.EMAIL_VERIFICATION: NotificationTypes.EMAIL_VERIFICATION_OTP,
    VerifyReason.PHONE_VERIFICATION: NotificationTypes.PHONE_VERIFICATION_OTP,
    VerifyReason.PROFILE_UPDATE: NotificationTypes.PROFILE_UPDATE_OTP,
}

web_token_notification_types = {
    VerifyReason.ONBOARDING: NotificationTypes.ONBOARDING_TOKEN_PASSWORD_RESET,
    VerifyReason.PASSWORD_RESET: NotificationTypes.WEB_TOKEN_PASSWORD_RESET,
    VerifyReason.RESEND_TOKEN: NotificationTypes.RESEND_WEB_TOKEN,
    VerifyReason.EMAIL_VERIFICATION: NotificationTypes.EMAIL_VERIFICATION_TOKEN,
    VerifyReason.PROFILE_UPDATE: NotificationTypes.PROFILE_UPDATE_TOKEN,
}


class UserVerification(UUIDPrimaryKey, BaseUserToken, CodeGenerator):
    VALIDITY_WINDOW = timedelta(hours=2)
    OTP_MAX_LENGTH = 5

    otp = models.CharField(max_length=OTP_MAX_LENGTH, null=True)
    token = models.CharField(max_length=255, null=True)
    notification_event = models.CharField(
        verbose_name=_("Notification event"),
        max_length=50,
        # choices=NotificationEvents.choices, # Not directly using choices from Enum for CharField
    )
    requested_at = models.DateTimeField(
        verbose_name=_("Request date"), auto_now_add=True
    )
    requested_by = models.ForeignKey(
        "accounts.AccountUser",
        related_name="verification_requests",
        on_delete=models.CASCADE,
    )
    is_used = models.BooleanField(
        verbose_name=_("Is used?"),
        default=False,
        help_text=_("Has this token been used successfully?"),
    )

    def save(self, *args, **kwargs) -> None:
        self.validate()
        super().save(*args, **kwargs)

    def validate(self):
        if not any((self.token, self.otp)):
            raise ValidationError("These fields cannot both be null")

    @classmethod
    def generate_token(
        cls, user: "AccountUser", reason: VerifyReason
    ) -> "UserVerification":
        token = secrets.token_urlsafe(nbytes=96)
        return cls.objects.create(
            token=token,
            requested_by=user,
            notification_event=web_token_notification_types[reason].value,
        )

    @classmethod
    def generate_otp(
        cls, user: "AccountUser", reason: VerifyReason
    ) -> "UserVerification":
        otp = cls.generate_code(length=cls.OTP_MAX_LENGTH)
        return cls.objects.create(
            otp=otp,
            requested_by=user,
            notification_event=otp_notification_types[reason].value,
        )

    @property
    def is_expired(self) -> bool:
        expires_at = self.requested_at + self.VALIDITY_WINDOW
        return self.is_used or timezone.now() > expires_at

    @transaction.atomic
    def mark_as_verified(self):
        self.is_used = True

        # Update the appropriate verification field based on the verification reason
        if self.notification_event in [
            NotificationTypes.EMAIL_VERIFICATION_OTP.value,
            NotificationTypes.EMAIL_VERIFICATION_TOKEN.value,
        ]:
            self.requested_by.is_verified = True
            self.requested_by.save(update_fields=["is_verified"])

        self.save(update_fields=["is_used"])

    @classmethod
    def generate_sms(
        cls, user: "AccountUser", reason: VerifyReason
    ) -> "UserVerification":
        """Generate an SMS verification code"""
        otp = cls.generate_code(length=cls.OTP_MAX_LENGTH)
        verification = cls.objects.create(
            otp=otp,
            requested_by=user,
            notification_event=otp_notification_types[reason].value,
        )
        # Note: The actual SMS sending would be implemented in a separate method
        return verification

    @classmethod
    def for_mode(
        cls, mode: VerifyMode, user: "AccountUser", reason: VerifyReason
    ) -> "UserVerification":
        """
        This method exists so that the client can determine which mode of verification it wants to opt for,
        at this point the application has no idea what verification mode to use.
        """
        VerificationStrategy = Callable[["AccountUser", VerifyReason], UserVerification]
        verification_strategies: dict[VerifyMode, VerificationStrategy] = {
            VerifyMode.OTP: cls.generate_otp,
            VerifyMode.TOKEN: cls.generate_token,
            VerifyMode.SMS: cls.generate_sms,
        }
        strategy = verification_strategies[mode]
        return strategy(user, reason)

    def send_mail(self):
        """Send verification email using AccountEmailSender."""
        user = self.requested_by
        try:
            email_type = NotificationTypes(self.notification_event)
        except ValueError:
            email_type = NotificationTypes.RESEND_OTP

        context = Context({
            "user_name": user.name,
            "otp": self.otp,
            "token": self.sign_token(reason=self.notification_event) if self.token else None,
            "user": user,
        })

        AccountEmailSender(
            recipients=[user.email_address],
            email_type=email_type,
            context=context,
        ).send()

    @property
    def to_email_address(self):
        return self.requested_by.email_address

    class Meta:
        default_permissions = []
        verbose_name = "user verification"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["requested_at"]),
            models.Index(fields=["requested_by"]),
        ]

    def __str__(self):
        return self.otp or self.token
