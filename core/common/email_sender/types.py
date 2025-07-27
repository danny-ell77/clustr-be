from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Union

from django.db import models
from django.template import Context, Template


class Sender(NamedTuple):
    name: str
    email: str


ClustRSupport = Sender(name="ClustR Support", email="support@clustr.com")
ClustRBilling = Sender(name="ClustR Billing", email="billing@clustr.com")
ClustRNoReply = Sender(name="ClustR", email="noreply@clustr.com")
ClustRGenericNotification = Sender(name="ClustR", email="notification@clustr.com")


class NotificationTypes(models.TextChoices):
    # Notification categories sent to account users.
    NEW_ADMIN_ONBOARDING = "NEW_ADMIN_ONBOARDING"
    NEW_SUBUSER_ACCOUNT_TO_SUBUSER = "NEW_SUBUSER_ACCOUNT_TO_SUBUSER"
    NEW_SUBUSER_ACCOUNT_TO_OWNER = "NEW_SUBUSER_ACCOUNT_TO_OWNER"
    SUBUSER_ACCOUNT_UPDATE = "SUBUSER_ACCOUNT_UPDATE"
    ONBOARDING_OTP_PASSWORD_RESET = "ONBOARDING_OTP_PASSWORD_RESET"
    ONBOARDING_TOKEN_PASSWORD_RESET = "ONBOARDING_TOKEN_PASSWORD_RESET"
    WEB_TOKEN_PASSWORD_RESET = "WEB_TOKEN_PASSWORD_RESET"
    OTP_PASSWORD_RESET = "OTP_PASSWORD_RESET"
    RESEND_OTP = "RESEND_OTP"
    RESEND_WEB_TOKEN = "RESEND_WEB_TOKEN"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    IMPORT_SUCCESS = "IMPORT_SUCCESS"
    EXPORT_SUCCESS = "EXPORT_SUCCESS"
    EMAIL_VERIFICATION_OTP = "EMAIL_VERIFICATION_OTP"
    PHONE_VERIFICATION_OTP = "PHONE_VERIFICATION_OTP"
    PROFILE_UPDATE_OTP = "PROFILE_UPDATE_OTP"
    EMAIL_VERIFICATION_TOKEN = "EMAIL_VERIFICATION_TOKEN"
    PROFILE_UPDATE_TOKEN = "PROFILE_UPDATE_TOKEN"

    # Access control
    SCHEDULED_VISIT_INVITATION = "SCHEDULED_VISIT_INVITATION"


class BodyTypes(str, Enum):
    TEXT = "TEXT"
    HTML = "HTML"


@dataclass(frozen=True, order=False)
class TransactionalEmail:
    from_name: str
    from_email_address: str
    to_emails: list[str]
    subject: Union[Template, str]
    body: Union[Template, str]
    preheader: str = ""
    context: Optional[Context] = None
    body_type: BodyTypes = BodyTypes.HTML
    reply_to_email_address: Optional[str] = None
    headers: Optional[dict] = None
    attachments: Optional[list] = None


class EmailAttribute(NamedTuple):
    template_name: str
    context: Context
    subject: str


DEFAULT_CONTEXT = Context()


class DeliveryStatuses(models.TextChoices):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    PENDING = "PENDING"
    BOUNCED = "BOUNCED"
    REJECTED = "REJECTED"
    SPAM = "SPAM"
    FAILED = "FAILED"


class SentEmailContent(NamedTuple):
    """Rendered email content sent to the recipient(s)"""

    subject: str
    body: str
    sender: str  # E.g. format: John Doe <johndoe@email.com>
    recipient: str
    status: DeliveryStatuses
    email_id: Optional[Union[str, int]] = None
    scheduled_task_id: Optional[str] = None
