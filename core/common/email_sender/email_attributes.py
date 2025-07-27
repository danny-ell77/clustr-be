from core.common.email_sender.types import (
    DEFAULT_CONTEXT,
    EmailAttribute,
    NotificationTypes,
)

DEFAULT_EMAIL_ATTRIBUTES: dict[NotificationTypes, EmailAttribute] = {
    NotificationTypes.NEW_ADMIN_ONBOARDING: EmailAttribute(
        template_name="new_admin_onboarding.html",
        context=DEFAULT_CONTEXT,
        subject="Welcome to ClustR",
    ),
    NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET: EmailAttribute(
        template_name="onboarding_otp_password_reset.html",
        context=DEFAULT_CONTEXT,
        subject="ClustR User Registration - Complete your registration",
    ),
    NotificationTypes.ONBOARDING_TOKEN_PASSWORD_RESET: EmailAttribute(
        template_name="onboarding_token_password_reset.html",
        context=DEFAULT_CONTEXT,
        subject="ClustR User Registration - Complete your registration",
    ),
    NotificationTypes.OTP_PASSWORD_RESET: EmailAttribute(
        template_name="otp_password_reset.html",
        context=DEFAULT_CONTEXT,
        subject="Password Reset Request",
    ),
    NotificationTypes.WEB_TOKEN_PASSWORD_RESET: EmailAttribute(
        template_name="web_token_password_reset.html",
        context=DEFAULT_CONTEXT,
        subject="Password Reset Request",
    ),
    NotificationTypes.IMPORT_SUCCESS: EmailAttribute(
        template_name="data_import_success.html",
        context=DEFAULT_CONTEXT,
        subject="Your data import is completed",
    ),
    NotificationTypes.EXPORT_SUCCESS: EmailAttribute(
        template_name="data_export_success.html",
        context=DEFAULT_CONTEXT,
        subject="Your data export is ready",
    ),
    NotificationTypes.NEW_SUBUSER_ACCOUNT_TO_SUBUSER: EmailAttribute(
        template_name="new_subuser_account_to_subuser.html",
        context=DEFAULT_CONTEXT,
        subject="You've been invited to join {{ cluster.name }}",
    ),
    NotificationTypes.NEW_SUBUSER_ACCOUNT_TO_OWNER: EmailAttribute(
        template_name="new_subuser_account_to_owner.html",
        context=DEFAULT_CONTEXT,
        subject="A new user has been added to your account",
    ),
    NotificationTypes.SCHEDULED_VISIT_INVITATION: EmailAttribute(
        template_name="scheduled_visit_invitation.html",
        context=DEFAULT_CONTEXT,
        subject="You've been to join {{ owner.name }} at {{ cluster.name }}",
    ),
}
