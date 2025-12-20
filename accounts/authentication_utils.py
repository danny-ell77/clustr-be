"""
Authentication utilities for ClustR application.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import AccountUser, UserVerification, VerifyMode, VerifyReason
from core.common.exceptions import AuthenticationException, ResourceNotFoundException
from core.common.models import Cluster

logger = logging.getLogger('clustr')

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



def handle_user_login(
    email_address: str,
    password: str,
    cluster_id: Optional[str] = None,
    remember_me: bool = False,
    device_name: Optional[str] = None,
    device_id: Optional[str] = None,
    request=None
) -> Dict[str, Any]:
    """
    Common function to handle user login for both members and accounts.
    
    Args:
        email_address: User's email address
        password: User's password
        cluster_id: Optional cluster ID for multi-tenant context
        remember_me: Whether to extend token lifetime
        device_name: Optional device name for logging
        device_id: Optional device ID for logging
        request: Optional request object for IP tracking
        
    Returns:
        Dict containing authentication tokens, user data, and permissions
        
    Raises:
        AuthenticationException: If authentication fails
    """
    from django.contrib.auth.models import Permission
    from accounts.authentication import generate_token
    
    try:
        user = AccountUser.objects.get(email_address=email_address)
        
        if check_account_lockout(user):
            raise AuthenticationException(
                _("Account is locked due to too many failed login attempts.")
            )
        
        if not user.check_password(password):
            handle_failed_login(user)
            raise AuthenticationException(_("Invalid credentials."))
        
        ip_address = get_client_ip(request) if request else None
        handle_successful_login(user, ip_address)
        
        if not cluster_id and user.primary_cluster:
            cluster_id = str(user.primary_cluster.id)
        
        expiry = None
        if remember_me:
            expiry = settings.JWT_EXTENDED_TOKEN_LIFETIME
        
        tokens = generate_token(user, cluster_id, expiry=expiry)
        
        tokens['user'] = {
            'email_address': user.email_address,
            'name': user.name,
            'phone_number': user.phone_number,
            'profile_image_url': user.profile_image_url,
            'is_verified': user.is_verified,
            'is_owner': user.is_owner,
            'is_cluster_admin': user.is_cluster_admin,
            'is_cluster_staff': user.is_cluster_staff,
        }
        
        if user.is_cluster_admin or user.is_superuser:
            permissions = list(Permission.objects.values_list('codename', flat=True))
        else:
            user_perms = set(user.user_permissions.values_list('codename', flat=True))
            group_perms = set(
                Permission.objects.filter(group__user=user)
                .values_list('codename', flat=True)
            )
            permissions = list(user_perms | group_perms)
        
        tokens['permissions'] = permissions
        
        logger.info(
            f"User logged in successfully: {user.email_address}",
            extra={
                "user_id": str(user.id),
                "cluster_id": cluster_id or "None",
                "ip_address": ip_address or "unknown",
                "device_name": device_name or "unknown",
                "device_id": device_id or "unknown",
                "remember_me": remember_me,
            }
        )
        
        return tokens
        
    except AccountUser.DoesNotExist:
        raise AuthenticationException(_("Invalid credentials."))


@transaction.atomic
def handle_user_registration(
    email_address: str,
    password: str,
    cluster_id: str,
    name: str,
    phone_number: Optional[str] = None,
    unit_address: Optional[str] = None,
    property_owner: bool = False,
    request=None,
    **extra_fields
) -> Dict[str, Any]:
    """
    Common function to handle user registration for both members and accounts.
    
    Args:
        email_address: User's email address
        password: User's password
        cluster_id: Cluster ID to associate with user
        name: User's name
        phone_number: Optional phone number
        unit_address: Optional unit address
        property_owner: Whether user is a property owner
        request: Optional request object for IP tracking
        **extra_fields: Additional fields to pass to user creation
        
    Returns:
        Dict containing authentication tokens
        
    Raises:
        ResourceNotFoundException: If cluster not found
    """
    from accounts.authentication import generate_token
    
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        
        user_data = {
            'email_address': email_address,
            'name': name,
        }
        
        if phone_number:
            user_data['phone_number'] = phone_number
        if unit_address:
            user_data['unit_address'] = unit_address
        if property_owner:
            user_data['property_owner'] = property_owner
            
        user_data.update(extra_fields)
        
        user = AccountUser.objects.create_owner(
            password=password,
            **user_data
        )
        
        user.clusters.add(cluster)
        user.primary_cluster = cluster
        user.save()
        
        verification = UserVerification.for_mode(
            VerifyMode.OTP, user, VerifyReason.EMAIL_VERIFICATION
        )
        verification.send_mail()
        
        tokens = generate_token(user, str(cluster.id))
        
        logger.info(
            f"User registered successfully: {user.email_address}",
            extra={
                "user_id": str(user.id),
                "cluster_id": str(cluster.id),
                "ip_address": get_client_ip(request) if request else "unknown",
            }
        )
        
        return tokens
        
    except Cluster.DoesNotExist:
        raise ResourceNotFoundException(_("Cluster not found."))
