"""
Async-compatible request middleware for ClustR application.

This middleware handles request processing in async environments, including:
- Generating a unique request ID for each request
- Storing the current request in context variables
- Logging request information
- Measuring request processing time
"""

import contextvars
import logging
import time
import uuid
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Context variables for async request storage
_request_context = contextvars.ContextVar("request", default=None)
_user_id_context = contextvars.ContextVar("user_id", default=None)
_cluster_id_context = contextvars.ContextVar("cluster_id", default=None)

# Configure logger
logger = logging.getLogger("clustr")


def get_current_request() -> Optional[HttpRequest]:
    """
    Get the current request from context variables.

    Returns:
        The current request or None if no request is available
    """
    return _request_context.get()


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from context variables.

    Returns:
        The current user ID or None if no user is authenticated
    """
    return _user_id_context.get()


def get_current_cluster_id() -> Optional[str]:
    """
    Get the current cluster ID from context variables.

    Returns:
        The current cluster ID or None if no cluster is selected
    """
    return _cluster_id_context.get()


class AsyncRequestMiddleware(MiddlewareMixin):
    """
    Async-compatible middleware to handle request processing.

    This middleware:
    - Generates a unique request ID for each request
    - Stores the current request in context variables
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

        # Store the current request in context variables
        _request_context.set(request)

        # Store user ID if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            _user_id_context.set(str(request.user.id))

        # Store cluster ID if available
        if hasattr(request, "cluster_context") and request.cluster_context:
            _cluster_id_context.set(str(request.cluster_context.id))

        # Store the start time for performance measurement
        request.start_time = time.time()

        # Log the request
        self._log_request(request)

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Process the response.

        Args:
            request: The request object
            response: The response object

        Returns:
            The response object
        """
        # Add the request ID to the response headers
        if hasattr(request, "id"):
            response["X-Request-ID"] = request.id

        # Log the response
        self._log_response(request, response)

        # Clear the context variables
        _request_context.set(None)
        _user_id_context.set(None)
        _cluster_id_context.set(None)

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
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        # Log the request
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                "request_id": request.id,
                "user_id": user_id,
                "method": request.method,
                "path": request.path,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
            },
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
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time

        # Get user information if available
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        # Log the response
        logger.info(
            f"Response: {request.method} {request.path} {response.status_code}",
            extra={
                "request_id": getattr(request, "id", None),
                "user_id": user_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration": duration,
            },
        )

        # Log slow requests
        if duration and duration > 1.0:  # Log requests that take more than 1 second
            logger.warning(
                f"Slow request: {request.method} {request.path} took {duration:.3f}s",
                extra={
                    "request_id": getattr(request, "id", None),
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.path,
                    "duration": duration,
                },
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
            "/static/",
            "/media/",
            "/health/",
            "/favicon.ico",
        ]

        return any(path.startswith(prefix) for prefix in skip_prefixes)
