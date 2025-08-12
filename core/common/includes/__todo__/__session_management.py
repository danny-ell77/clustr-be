"""
Session management utilities for ClustR application.
"""

import hashlib
import json
from datetime import timedelta
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from typing import Dict, List, Optional, Any



class SessionManager:
    """Manager for user session operations."""
    
    @classmethod
    def create_session(cls, user, request) -> 'UserSession':
        """
        Create a new user session record.
        
        Args:
            user: The user creating the session
            request: The HTTP request object
            
        Returns:
            UserSession instance
        """
        from accounts.models import UserSession
        
        # Get session timeout from security settings
        security_settings = getattr(user, 'security_settings', None)
        timeout_minutes = security_settings.session_timeout_minutes if security_settings else 480
        
        # Extract session information
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_fingerprint = cls.generate_device_fingerprint(request)
        location_info = cls.get_location_info(ip_address)
        
        # Create session record
        expires_at = timezone.now() + timedelta(minutes=timeout_minutes)
        
        session = UserSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            location_info=location_info,
            expires_at=expires_at
        )
        
        # Check concurrent session limit
        cls.enforce_session_limit(user)
        
        # Send login notification if enabled
        cls.send_login_notification(user, session)
        
        return session
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """
        Get the client IP address from the request.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'
    
    @classmethod
    def generate_device_fingerprint(cls, request) -> str:
        """
        Generate a device fingerprint from request headers.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Device fingerprint hash
        """
        # Collect fingerprinting data
        fingerprint_data = {
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            'accept_encoding': request.META.get('HTTP_ACCEPT_ENCODING', ''),
            'accept': request.META.get('HTTP_ACCEPT', ''),
        }
        
        # Create hash
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:64]
    
    @classmethod
    def get_location_info(cls, ip_address: str) -> dict[str, Any]:
        """
        Get approximate location information for an IP address.
        
        Args:
            ip_address: The IP address to lookup
            
        Returns:
            Dictionary with location information
        """
        # For now, return basic info
        # In production, you might use a service like MaxMind GeoIP
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown'
        }
    
    @classmethod
    def enforce_session_limit(cls, user) -> None:
        """
        Enforce maximum concurrent session limit for a user.
        
        Args:
            user: The user to check session limits for
        """
        from accounts.models import UserSession
        
        security_settings = getattr(user, 'security_settings', None)
        max_sessions = security_settings.max_concurrent_sessions if security_settings else 5
        
        # Get active sessions ordered by last activity
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-last_activity')
        
        # If we exceed the limit, terminate oldest sessions
        if active_sessions.count() > max_sessions:
            sessions_to_terminate = active_sessions[max_sessions:]
            for session in sessions_to_terminate:
                cls.terminate_session(session)
    
    @classmethod
    def terminate_session(cls, session) -> None:
        """
        Terminate a user session.
        
        Args:
            session: The UserSession to terminate
        """
        # Mark session as inactive
        session.terminate()
        
        # Delete Django session if it exists
        try:
            django_session = Session.objects.get(session_key=session.session_key)
            django_session.delete()
        except Session.DoesNotExist:
            pass
    
    @classmethod
    def terminate_all_sessions(cls, user, except_current: Optional[str] = None) -> int:
        """
        Terminate all sessions for a user.
        
        Args:
            user: The user whose sessions to terminate
            except_current: Session key to exclude from termination
            
        Returns:
            Number of sessions terminated
        """
        from accounts.models import UserSession
        
        sessions_query = UserSession.objects.filter(user=user, is_active=True)
        
        if except_current:
            sessions_query = sessions_query.exclude(session_key=except_current)
        
        sessions = list(sessions_query)
        
        for session in sessions:
            cls.terminate_session(session)
        
        return len(sessions)
    
    @classmethod
    def extend_session(cls, session, minutes: Optional[int] = None) -> None:
        """
        Extend a session's expiry time.
        
        Args:
            session: The UserSession to extend
            minutes: Minutes to extend (uses security settings if not provided)
        """
        session.extend_session(minutes)
    
    @classmethod
    def is_session_valid(cls, session) -> bool:
        """
        Check if a session is valid (active and not expired).
        
        Args:
            session: The UserSession to check
            
        Returns:
            True if session is valid, False otherwise
        """
        return session.is_active and not session.is_expired()
    
    @classmethod
    def get_user_sessions(cls, user) -> List['UserSession']:
        """
        Get all active sessions for a user.
        
        Args:
            user: The user to get sessions for
            
        Returns:
            List of active UserSession objects
        """
        from accounts.models import UserSession
        
        return UserSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-last_activity')
    
    @classmethod
    def send_login_notification(cls, user, session) -> None:
        """
        Send login notification if enabled in security settings.
        
        Args:
            user: The user who logged in
            session: The UserSession created
        """
        security_settings = getattr(user, 'security_settings', None)
        if not security_settings or not security_settings.login_notifications_enabled:
            return
        
        # Check if this is a new device
        is_new_device = not security_settings.is_trusted_device(session.device_fingerprint)
        
        if is_new_device:
            notifications.send(
                event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for a more specific login notification event
                recipients=[user],
                cluster=user.cluster, # Assuming user has a cluster attribute
                context={
                    "time": session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "ip_address": session.ip_address,
                    "device": session.user_agent[:100],
                    "location": f"{session.location_info.get('city', 'Unknown')}, {session.location_info.get('country', 'Unknown')}",
                }
            )
    
    @classmethod
    def detect_suspicious_activity(cls, user, request) -> dict[str, Any]:
        """
        Detect suspicious login activity.
        
        Args:
            user: The user attempting to log in
            request: The HTTP request object
            
        Returns:
            Dictionary with detection results
        """
        from accounts.models import LoginAttempt
        
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for rapid login attempts from different IPs
        recent_attempts = LoginAttempt.objects.filter(
            user=user,
            attempted_at__gte=timezone.now() - timedelta(hours=1)
        ).values('ip_address').distinct()
        
        if recent_attempts.count() > 3:
            return {
                'suspicious': True,
                'reason': 'Multiple IP addresses in short time',
                'action': 'require_2fa'
            }
        
        # Check for login from new location
        recent_sessions = cls.get_user_sessions(user)
        known_ips = [session.ip_address for session in recent_sessions[-10:]]  # Last 10 sessions
        
        if ip_address not in known_ips and len(known_ips) > 0:
            return {
                'suspicious': True,
                'reason': 'Login from new IP address',
                'action': 'send_notification'
            }
        
        return {
            'suspicious': False
        }
    
    @classmethod
    def log_login_attempt(cls, user, request, success: bool, failure_reason: str = '') -> None:
        """
        Log a login attempt for security monitoring.
        
        Args:
            user: The user attempting to log in (can be None for failed attempts)
            request: The HTTP request object
            success: Whether the login was successful
            failure_reason: Reason for failure (if applicable)
        """
        from accounts.models import LoginAttempt
        
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        location_info = cls.get_location_info(ip_address)
        
        # Get email from request if user is None
        email_address = user.email_address if user else request.POST.get('email_address', '')
        
        LoginAttempt.objects.create(
            user=user,
            email_address=email_address,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            location_info=location_info
        )
    
    @classmethod
    def cleanup_expired_sessions(cls) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        from accounts.models import UserSession
        
        expired_sessions = UserSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        count = expired_sessions.count()
        
        for session in expired_sessions:
            cls.terminate_session(session)
        
        return count


class DeviceManager:
    """Manager for trusted device operations."""
    
    @classmethod
    def add_trusted_device(cls, user, request, device_name: str = '') -> dict[str, Any]:
        """
        Add a device to the user's trusted devices list.
        
        Args:
            user: The user adding the device
            request: The HTTP request object
            device_name: Optional name for the device
            
        Returns:
            Dictionary with result
        """
        security_settings = getattr(user, 'security_settings', None)
        if not security_settings:
            return {
                'success': False,
                'error': _('Security settings not found.')
            }
        
        device_fingerprint = SessionManager.generate_device_fingerprint(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        device_info = {
            'name': device_name or cls.parse_device_name(user_agent),
            'user_agent': user_agent,
            'ip_address': SessionManager.get_client_ip(request),
            'last_used': timezone.now().isoformat()
        }
        
        security_settings.add_trusted_device(device_fingerprint, device_info)
        
        return {
            'success': True,
            'message': _('Device added to trusted devices.')
        }
    
    @classmethod
    def remove_trusted_device(cls, user, device_fingerprint: str) -> dict[str, Any]:
        """
        Remove a device from the user's trusted devices list.
        
        Args:
            user: The user removing the device
            device_fingerprint: The device fingerprint to remove
            
        Returns:
            Dictionary with result
        """
        security_settings = getattr(user, 'security_settings', None)
        if not security_settings:
            return {
                'success': False,
                'error': _('Security settings not found.')
            }
        
        security_settings.remove_trusted_device(device_fingerprint)
        
        return {
            'success': True,
            'message': _('Device removed from trusted devices.')
        }
    
    @classmethod
    def parse_device_name(cls, user_agent: str) -> str:
        """
        Parse a human-readable device name from user agent.
        
        Args:
            user_agent: The user agent string
            
        Returns:
            Human-readable device name
        """
        # Simple parsing - in production you might use a library like user-agents
        if 'Mobile' in user_agent or 'Android' in user_agent:
            if 'Android' in user_agent:
                return 'Android Device'
            elif 'iPhone' in user_agent:
                return 'iPhone'
            elif 'iPad' in user_agent:
                return 'iPad'
            else:
                return 'Mobile Device'
        elif 'Windows' in user_agent:
            return 'Windows Computer'
        elif 'Mac' in user_agent:
            return 'Mac Computer'
        elif 'Linux' in user_agent:
            return 'Linux Computer'
        else:
            return 'Unknown Device'
    
    @classmethod
    def is_trusted_device(cls, user, request) -> bool:
        """
        Check if the current device is trusted.
        
        Args:
            user: The user to check
            request: The HTTP request object
            
        Returns:
            True if device is trusted, False otherwise
        """
        security_settings = getattr(user, 'security_settings', None)
        if not security_settings:
            return False
        
        device_fingerprint = SessionManager.generate_device_fingerprint(request)
        return security_settings.is_trusted_device(device_fingerprint)