from django.utils import timezone

from accounts.models import PRIMARY_ROLE_NAME, AccountUser, UserVerification, Role
from core.notifications.events import NotificationEvents


def create_mock_email_verification(owner, otp=None, token=None, **kwargs):
    assert any((otp, token)), "An OTP or Token must be passed"
    valid_data = {
        "otp": otp,
        "token": token,
        "requested_at": timezone.now(),
        "requested_by": owner,
        "notification_type": NotificationEvents.SYSTEM_UPDATE.value, # Placeholder
    }
    valid_data.update(kwargs)
    return valid_data, UserVerification.objects.create(**valid_data)


def create_mock_role(
    owner: AccountUser, name: str = PRIMARY_ROLE_NAME
) -> tuple[dict, Role]:
    valid_payload = {
        "owner": owner,
        "name": name,
        "description": "Test description",
        "created_by": owner.pk,
    }
    role: Role = Role.objects.create(**valid_payload)
    valid_payload["owner"] = owner.pk
    return valid_payload, role


def create_previous_password(): ...
