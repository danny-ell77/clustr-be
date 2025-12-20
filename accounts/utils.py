from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from accounts.models import AccountUser
from django.utils.crypto import get_random_string

ALLOWED_CHARS = (
    """abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789#$%&()+-/<=>?@[\]"""
)

PASSWORD_LENGTH = 20


def generate_strong_password() -> str:
    return get_random_string(
        length=PASSWORD_LENGTH, allowed_chars=ALLOWED_CHARS
    )


def change_password(*, user, new_password, current_password=None, force_logout=False, notify=True):
    """
    Change a user's password with enhanced security features.
    
    Args:
        user: The user whose password is being changed
        new_password: The new password
        current_password: The current password (optional for admin-initiated changes)
        force_logout: Whether to invalidate all existing tokens
        notify: Whether to send a notification email
    """
    if current_password:
        _validate_current_password(current_password, new_password, user)
    _validate_new_password(new_password, user)

    # Store the current password hash for history
    hashed_current_password = (
        make_password(current_password) if current_password else user.password
    )
    
    # Set the new password
    user.set_password(new_password)
    
    # Reset security-related fields
    user.failed_login_attempts = 0
    user.account_locked_until = None
    
    # Save the user
    user.save(update_fields=["password", "failed_login_attempts", "account_locked_until"])
    
    # Update password history
    if not hasattr(user, 'previous_passwords'):
        from accounts.models import PreviousPasswords
        PreviousPasswords.objects.create(user=user, passwords=[hashed_current_password])
    else:
        # Limit the number of stored passwords (e.g., keep last 10)
        max_stored_passwords = 10
        user.previous_passwords.passwords.append(hashed_current_password)
        if len(user.previous_passwords.passwords) > max_stored_passwords:
            user.previous_passwords.passwords = user.previous_passwords.passwords[-max_stored_passwords:]
        user.previous_passwords.save(update_fields=["passwords"])
    
    # Force logout if requested
    if force_logout:
        logout_user(user)
    
    # Send notification email
    if notify:
        from core.common.email_sender import AccountEmailSender
        from core.common.email_sender.types import NotificationTypes
        
        AccountEmailSender(
            recipients=[user.email_address],
            email_type=NotificationTypes.PASSWORD_CHANGED,
            context={"user_name": user.name}
        ).send()


def logout_user(user):
    try:
        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
    except TokenError as e:
        raise InvalidToken(e.args[0])


def _validate_new_password(new_password, user):
    if user.check_password(new_password):
        raise ValidationError(
            {"detail": "Choose a password you haven't previously used"}
        )

    for previous_password in user.previous_passwords.passwords:
        if check_password(new_password, previous_password):
            raise ValidationError(
                {"detail": "Choose a password you haven't previously used"}
            )
    try:
        validate_password(password=new_password, user=user)
    except exceptions.ValidationError as e:
        raise ValidationError(e.messages)


def _validate_current_password(current_password, new_password, user):
    if not user.check_password(current_password):
        raise ValidationError({"detail": "Incorrect password"})
    if not new_password:
        raise ValidationError(
            {"detail": "This field is required if you're changing your password"}
        )
    if user.check_password(new_password):
        raise ValidationError(
            {"detail": "Choose a password you haven't previously used"}
        )
