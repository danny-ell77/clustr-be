"""
JWT Authentication for ClustR application.
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import authentication, exceptions
from rest_framework.request import Request

from accounts.models import AccountUser
from core.common.error_utils import log_exception_with_context

# Configure logger
logger = logging.getLogger("clustr")


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Enhanced JWT authentication for ClustR application.
    Supports multi-tenant architecture with cluster context and improved security features.
    """

    def authenticate(
        self, request: Request
    ) -> Optional[tuple[AccountUser, dict[str, Any]]]:
        """
        Authenticate the request and return a two-tuple of (user, token_payload).
        """
        jwt_token = self.get_token_from_request(request)
        if not jwt_token:
            return None

        try:
            # Decode and validate the token
            payload = self.decode_token(jwt_token)

            # Validate token type
            if payload.get("token_type") != "access":
                raise exceptions.AuthenticationFailed(_("Invalid token type."))

            # Get the user from the payload
            user = self.get_user_from_payload(payload)

            # Check for account lockout
            from accounts.authentication_utils import check_account_lockout

            if check_account_lockout(user):
                raise exceptions.AuthenticationFailed(
                    _("Account is locked due to too many failed login attempts.")
                )

            # Set cluster context in request if present in token
            self.set_cluster_context(request, user, payload)

            # Record the authentication in the request for audit logging
            request._auth_user_id = str(user.id)
            request._auth_token = jwt_token

            return (user, payload)
        except jwt.ExpiredSignatureError:
            log_exception_with_context(
                Exception("JWT token expired"),
                log_level=logging.INFO,
                request=request,
                context={
                    "token_header": request.headers.get("Authorization", "")[:20]
                    + "..."
                },
            )
            raise exceptions.AuthenticationFailed(_("Token has expired."))
        except jwt.DecodeError:
            log_exception_with_context(
                Exception("JWT decode error"),
                log_level=logging.WARNING,
                request=request,
            )
            raise exceptions.AuthenticationFailed(_("Invalid token."))
        except jwt.InvalidTokenError:
            log_exception_with_context(
                Exception("Invalid JWT token"),
                log_level=logging.WARNING,
                request=request,
            )
            raise exceptions.AuthenticationFailed(_("Invalid token."))
        except AccountUser.DoesNotExist:
            log_exception_with_context(
                Exception("User not found for JWT token"),
                log_level=logging.WARNING,
                request=request,
            )
            raise exceptions.AuthenticationFailed(_("User not found."))
        except exceptions.AuthenticationFailed:
            # Re-raise authentication failures
            raise
        except Exception as e:
            # Log unexpected errors
            log_exception_with_context(e, log_level=logging.ERROR, request=request)
            raise exceptions.AuthenticationFailed(_("Authentication failed."))

    def set_cluster_context(
        self, request: Request, user: AccountUser, payload: dict[str, Any]
    ) -> None:
        """
        Set the cluster context in the request based on the token payload.

        Args:
            request: The request object
            user: The authenticated user
            payload: The token payload
        """
        # Check for cluster_id in payload
        if "cluster_id" in payload:
            cluster_id = payload["cluster_id"]

            # Check if user has access to this cluster
            if user.clusters.filter(id=cluster_id).exists():
                # Set cluster context in request
                request.cluster = user.clusters.get(id=cluster_id)
            else:
                raise exceptions.AuthenticationFailed(
                    _("Invalid cluster context in token.")
                )

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract the JWT token from the request.

        Args:
            request: The request object

        Returns:
            The JWT token if found, None otherwise
        """
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]

        # Check for token in cookies (if enabled)
        if getattr(settings, "JWT_COOKIE_AUTHENTICATION", False):
            token = request.COOKIES.get(
                getattr(settings, "JWT_COOKIE_NAME", "clustr_token")
            )
            if token:
                return token

        return None

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        Decode the JWT token and return the payload.

        Args:
            token: The JWT token to decode

        Returns:
            The decoded token payload
        """
        # Use settings.SECRET_KEY as the default key
        secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)

        # Get the allowed algorithms
        algorithms = getattr(settings, "JWT_ALGORITHMS", ["HS256"])

        # Decode the token with validation
        return jwt.decode(
            token,
            secret_key,
            algorithms=algorithms,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "iat", "user_id", "token_type"],
            },
        )

    def get_user_from_payload(self, payload: dict[str, Any]) -> AccountUser:
        """
        Get the user from the token payload.

        Args:
            payload: The token payload

        Returns:
            The user object
        """
        user_id = payload.get("user_id")
        if not user_id:
            raise exceptions.AuthenticationFailed(_("Invalid token payload."))

        try:
            user = (
                AccountUser.objects.select_related("primary_cluster", "owner")
                .prefetch_related("clusters")
                .get(id=user_id)
            )

            # Check if user is active
            if not user.is_active:
                raise exceptions.AuthenticationFailed(_("User is inactive."))

            # Check if user is verified (if required)
            if (
                getattr(settings, "REQUIRE_VERIFIED_EMAIL", True)
                and not user.is_verified
            ):
                raise exceptions.AuthenticationFailed(_("Email address not verified."))

            return user
        except AccountUser.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("User not found."))


def generate_token(
    user: AccountUser,
    cluster_id: Optional[str] = None,
    expiry: Optional[timedelta] = None,
) -> dict[str, str]:
    """
    Generate a JWT token for the given user.

    Args:
        user: The user to generate the token for
        cluster_id: Optional cluster ID to include in the token
        expiry: Optional token expiry time

    Returns:
        Dict containing access_token and refresh_token
    """
    # Use settings or default values
    access_token_expiry = expiry or timedelta(
        hours=getattr(settings, "JWT_ACCESS_TOKEN_LIFETIME_HOURS", 1)
    )
    refresh_token_expiry = timedelta(
        days=getattr(settings, "JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7)
    )

    # Current time for token issuance
    now = datetime.utcnow()

    # Generate a unique token ID (jti) for token revocation support
    import uuid

    token_id = str(uuid.uuid4())

    # Create the access token payload
    access_payload = {
        "user_id": str(user.id),
        "email": user.email_address,
        "name": user.name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_cluster_admin": user.is_cluster_admin,
        "is_cluster_staff": user.is_cluster_staff,
        "token_type": "access",  # Explicitly set token type
        "jti": token_id,  # JWT ID for token revocation
        "iat": now,
        "exp": now + access_token_expiry,
    }

    # Add cluster context if provided
    if cluster_id:
        access_payload["cluster_id"] = cluster_id

    # Create the refresh token payload
    refresh_payload = {
        "user_id": str(user.id),
        "token_type": "refresh",
        "jti": f"{token_id}-refresh",  # Related JWT ID for refresh token
        "iat": now,
        "exp": now + refresh_token_expiry,
    }

    # Add cluster context to refresh token if provided
    if cluster_id:
        refresh_payload["cluster_id"] = cluster_id

    # Use settings.SECRET_KEY as the default key
    secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

    # Generate the tokens
    access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)

    # Log token generation (without sensitive details)
    logger.info(
        f"Generated tokens for user: {user.email_address}",
        extra={
            "user_id": str(user.id),
            "token_id": token_id,
            "cluster_id": cluster_id or "None",
        },
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(access_token_expiry.total_seconds()),
    }


def refresh_token(
    refresh_token_str: str, request: Optional[Request] = None
) -> dict[str, str]:
    """
    Generate a new access token using a refresh token.

    Args:
        refresh_token_str: The refresh token string
        request: Optional request object for logging purposes

    Returns:
        Dict containing new access_token and refresh_token
    """
    # Use settings.SECRET_KEY as the default key
    secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
    algorithms = getattr(settings, "JWT_ALGORITHMS", ["HS256"])

    try:
        # Decode the refresh token with strict validation
        payload = jwt.decode(
            refresh_token_str,
            secret_key,
            algorithms=algorithms,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "iat", "user_id", "token_type", "jti"],
            },
        )

        # Verify it's a refresh token
        if payload.get("token_type") != "refresh":
            log_exception_with_context(
                Exception("Invalid token type during refresh"),
                log_level=logging.WARNING,
                request=request,
                context={"token_type": payload.get("token_type")},
            )
            raise exceptions.AuthenticationFailed(_("Invalid refresh token."))

        # Get the user
        user_id = payload.get("user_id")
        if not user_id:
            log_exception_with_context(
                Exception("Missing user_id in refresh token"),
                log_level=logging.WARNING,
                request=request,
            )
            raise exceptions.AuthenticationFailed(_("Invalid token payload."))

        try:
            user = AccountUser.objects.get(id=user_id)

            # Check if user is active
            if not user.is_active:
                log_exception_with_context(
                    Exception("Inactive user attempted token refresh"),
                    log_level=logging.WARNING,
                    request=request,
                    context={"user_id": user_id},
                )
                raise exceptions.AuthenticationFailed(_("User is inactive."))

            # Check for account lockout
            from accounts.authentication_utils import check_account_lockout

            if check_account_lockout(user):
                log_exception_with_context(
                    Exception("Locked account attempted token refresh"),
                    log_level=logging.WARNING,
                    request=request,
                    context={"user_id": user_id},
                )
                raise exceptions.AuthenticationFailed(
                    _("Account is locked due to too many failed login attempts.")
                )

            # Get cluster context from token
            cluster_id = payload.get("cluster_id")

            # Check if token has been revoked (would be implemented in a TokenBlacklist model)
            # This is a placeholder for future implementation
            # if is_token_revoked(payload.get('jti')):
            #     raise exceptions.AuthenticationFailed(_('Token has been revoked.'))

            # Generate new tokens
            new_tokens = generate_token(user, cluster_id)

            # Log successful token refresh
            logger.info(
                f"Token refreshed for user: {user.email_address}",
                extra={"user_id": str(user.id), "cluster_id": cluster_id or "None"},
            )

            return new_tokens

        except AccountUser.DoesNotExist:
            log_exception_with_context(
                Exception("User not found during token refresh"),
                log_level=logging.WARNING,
                request=request,
                context={"user_id": user_id},
            )
            raise exceptions.AuthenticationFailed(_("User not found."))

    except jwt.ExpiredSignatureError:
        log_exception_with_context(
            Exception("Expired refresh token"), log_level=logging.INFO, request=request
        )
        raise exceptions.AuthenticationFailed(_("Refresh token has expired."))
    except jwt.DecodeError:
        log_exception_with_context(
            Exception("Invalid refresh token - decode error"),
            log_level=logging.WARNING,
            request=request,
        )
        raise exceptions.AuthenticationFailed(_("Invalid refresh token."))
    except jwt.InvalidTokenError:
        log_exception_with_context(
            Exception("Invalid refresh token"),
            log_level=logging.WARNING,
            request=request,
        )
        raise exceptions.AuthenticationFailed(_("Invalid refresh token."))
    except Exception as e:
        # Log unexpected errors
        log_exception_with_context(e, log_level=logging.ERROR, request=request)
        raise exceptions.AuthenticationFailed(_("Token refresh failed."))
