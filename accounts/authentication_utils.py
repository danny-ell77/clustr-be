"""
Authentication utilities for ClustR application.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import AccountUser
from core.common.exceptions import AuthenticationException

# Configure logger
logger = logging.getLogger('clustr')

# Default settings for account lockout
DEFAULT_MAX_LOGIN_ATTEMPTS = 5
DEFAULT_LOCKOUT_DURATION_MINUTES = 30


def check_account_lockout(user: AccountUser) -> bool:
    """
    Check if a user account is locked due to too many failed login attempts.
    
    Args:
        user: The user to check
        
    Returns:
        True if the account is locked, False otherwise
    """
    # If account_locked_until is set and in the future, the account is locked
    if user.account_locked_until and user.account_locked_until > timezone.now():
        # Log the lockout attempt
        logger.warning(
            f"Login attempt for locked account: {user.email_address}",
            extra={
                'user_id': str(user.id),
                'locked_until': user.account_locked_until.isoformat(),
                'remaining_time': (user.account_locked_until - timezone.now()).total_seconds() // 60
            }
        )
        return True
    
    return False


def handle_failed_login(user: AccountUser) -> None:
    """
    Handle a failed login attempt for a user.
    
    This function increments the failed login counter and locks the account
    if the maximum number of attempts is reached.
    
    Args:
        user: The user who failed to log in
    """
    # Get settings
    max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', DEFAULT_MAX_LOGIN_ATTEMPTS)
    lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION_MINUTES', DEFAULT_LOCKOUT_DURATION_MINUTES)
    
    # Update failed login attempts
    user.last_failed_login = timezone.now()
    user.failed_login_attempts += 1
    
    # Check if account should be locked
    if user.failed_login_attempts >= max_attempts:
        user.account_locked_until = timezone.now() + timedelta(minutes=lockout_duration)
        logger.warning(
            f"Account locked due to too many failed login attempts: {user.email_address}",
            extra={
                'user_id': str(user.id),
                'failed_attempts': user.failed_login_attempts,
                'locked_until': user.account_locked_until.isoformat()
            }
        )
    
    # Save the user
    user.save(update_fields=['last_failed_login', 'failed_login_attempts', 'account_locked_until'])


def handle_successful_login(user: AccountUser, ip_address: Optional[str] = None) -> None:
    """
    Handle a successful login attempt for a user.
    
    This function resets the failed login counter and updates the last login information.
    
    Args:
        user: The user who successfully logged in
        ip_address: The IP address of the login attempt
    """
    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.account_locked_until = None
    
    # Update last login IP if provided
    if ip_address:
        user.last_login_ip = ip_address
    
    # Save the user
    update_fields = ['failed_login_attempts', 'account_locked_until']
    if ip_address:
        update_fields.append('last_login_ip')
    
    user.save(update_fields=update_fields)
    
    logger.info(
        f"Successful login: {user.email_address}",
        extra={
            'user_id': str(user.id),
            'ip_address': ip_address or 'unknown'
        }
    )


def get_client_ip(request) -> str:
    """
    Get the client IP address from a request.
    
    Args:
        request: The request object
        
    Returns:
        The client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list of IPs.
        # The client's IP will be the first one.
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip