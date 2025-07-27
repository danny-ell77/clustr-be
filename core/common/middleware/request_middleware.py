"""
Request middleware for ClustR application.

This middleware handles request processing, including:
- Generating a unique request ID for each request
- Storing the current request in thread local storage
- Logging request information
- Measuring request processing time
"""

import logging
import threading
import time
import uuid
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Thread local storage for the current request
_thread_local = threading.local()

# Configure logger
logger = logging.getLogger('clustr')


def get_current_request() -> Optional[HttpRequest]:
    """
    Get the current request from thread local storage.
    
    Returns:
        The current request or None if no request is available
    """
    return getattr(_thread_local, 'request', None)


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from the request.
    
    Returns:
        The current user ID or None if no user is authenticated
    """
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return str(request.user.id)
    return None


def get_current_cluster_id() -> Optional[str]:
    """
    Get the current cluster ID from the request.
    
    Returns:
        The current cluster ID or None if no cluster is selected
    """
    request = get_current_request()
    if request and hasattr(request, 'cluster_context') and request.cluster_context:
        return str(request.cluster_context.id)
    return None


class RequestMiddleware(MiddlewareMixin):
    """
    Middleware to handle request processing.
    
    This middleware:
    - Generates a unique request ID for each request
    - Stores the current request in thread local storage
    - Logs request information
    - Measures request processing time
    """
    
    def process_request(self, request: HttpRequest) -> None:
        """
        Process the request.
        
        Args:
            request: The request object
            
        Returns:
            None
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.id = request_id
        
        # Store the current request in thread local storage
        _thread_local.request = request
        
        # Store the start time for performance measurement
        request.start_time = time.time()
        
        # Log the request
        self._log_request(request)
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process the response.
        
        Args:
            request: The request object
            response: The response object
            
        Returns:
            The response object
        """
        # Add the request ID to the response headers
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id
        
        # Log the response
        self._log_response(request, response)
        
        # Clear the thread local storage
        if hasattr(_thread_local, 'request'):
            del _thread_local.request
        
        return response
    
    def _log_request(self, request: HttpRequest) -> None:
        """
        Log the request.
        
        Args:
            request: The request object
        """
        # Skip logging for certain paths
        if self._should_skip_logging(request.path):
            return
        
        # Get user information if available
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
        
        # Log the request
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'request_id': request.id,
                'user_id': user_id,
                'method': request.method,
                'path': request.path,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
            }
        )
    
    def _log_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """
        Log the response.
        
        Args:
            request: The request object
            response: The response object
        """
        # Skip logging for certain paths
        if self._should_skip_logging(request.path):
            return
        
        # Calculate the request duration
        duration = None
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        
        # Get user information if available
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
        
        # Log the response
        logger.info(
            f"Response: {request.method} {request.path} {response.status_code}",
            extra={
                'request_id': getattr(request, 'id', None),
                'user_id': user_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': duration,
            }
        )
        
        # Log slow requests
        if duration and duration > 1.0:  # Log requests that take more than 1 second
            logger.warning(
                f"Slow request: {request.method} {request.path} took {duration:.3f}s",
                extra={
                    'request_id': getattr(request, 'id', None),
                    'user_id': user_id,
                    'method': request.method,
                    'path': request.path,
                    'duration': duration,
                }
            )
    
    def _should_skip_logging(self, path: str) -> bool:
        """
        Determine if logging should be skipped for the given path.
        
        Args:
            path: The request path
            
        Returns:
            True if logging should be skipped, False otherwise
        """
        # Skip logging for static files, media files, and health checks
        skip_prefixes = [
            '/static/',
            '/media/',
            '/health/',
            '/favicon.ico',
        ]
        
        return any(path.startswith(prefix) for prefix in skip_prefixes)