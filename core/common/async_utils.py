"""
Async utilities for ClustR application.

This module provides utility functions for handling request context in async environments.
"""

from typing import Callable, Optional, TypeVar

from django.http import HttpRequest

from core.common.middleware.async_request_middleware import (
    get_current_request,
    get_current_user_id,
    get_current_cluster_id,
)

# Type variable for function return type
T = TypeVar("T")


def with_request_context(request: HttpRequest):
    """
    Context manager to set request context for async operations.

    Args:
        request: The request object to set in context

    Returns:
        A context manager that sets the request context
    """

    # Get the context variables from the async middleware
    from core.common.middleware.async_request_middleware import (
        _request_context,
        _user_id_context,
        _cluster_id_context,
    )

    class RequestContextManager:
        def __enter__(self):
            # Store the current context
            self._old_request = _request_context.get()
            self._old_user_id = _user_id_context.get()
            self._old_cluster_id = _cluster_id_context.get()

            # Set the new context
            _request_context.set(request)

            # Set user ID if authenticated
            if hasattr(request, "user") and request.user.is_authenticated:
                _user_id_context.set(str(request.user.id))

            # Set cluster ID if available
            if hasattr(request, "cluster_context") and request.cluster_context:
                _cluster_id_context.set(str(request.cluster_context.id))

            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore the old context
            _request_context.set(self._old_request)
            _user_id_context.set(self._old_user_id)
            _cluster_id_context.set(self._old_cluster_id)

    return RequestContextManager()


def async_with_request_context(request: HttpRequest):
    """
    Async context manager to set request context for async operations.

    Args:
        request: The request object to set in context

    Returns:
        An async context manager that sets the request context
    """

    # Get the context variables from the async middleware
    from core.common.middleware.async_request_middleware import (
        _request_context,
        _user_id_context,
        _cluster_id_context,
    )

    class AsyncRequestContextManager:
        async def __aenter__(self):
            # Store the current context
            self._old_request = _request_context.get()
            self._old_user_id = _user_id_context.get()
            self._old_cluster_id = _cluster_id_context.get()

            # Set the new context
            _request_context.set(request)

            # Set user ID if authenticated
            if hasattr(request, "user") and request.user.is_authenticated:
                _user_id_context.set(str(request.user.id))

            # Set cluster ID if available
            if hasattr(request, "cluster_context") and request.cluster_context:
                _cluster_id_context.set(str(request.cluster_context.id))

            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Restore the old context
            _request_context.set(self._old_request)
            _user_id_context.set(self._old_user_id)
            _cluster_id_context.set(self._old_cluster_id)

    return AsyncRequestContextManager()


def run_in_request_context(
    func: Callable[..., T], request: HttpRequest, *args, **kwargs
) -> T:
    """
    Run a function with request context.

    Args:
        func: The function to run
        request: The request object
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function
    """
    with with_request_context(request):
        return func(*args, **kwargs)


async def run_async_in_request_context(
    func: Callable[..., T], request: HttpRequest, *args, **kwargs
) -> T:
    """
    Run an async function with request context.

    Args:
        func: The async function to run
        request: The request object
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function
    """
    async with async_with_request_context(request):
        return await func(*args, **kwargs)


def get_async_current_request() -> Optional[HttpRequest]:
    """
    Get the current request in async context.

    Returns:
        The current request or None if no request is available
    """
    return get_current_request()


def get_async_current_user_id() -> Optional[str]:
    """
    Get the current user ID in async context.

    Returns:
        The current user ID or None if no user is authenticated
    """
    return get_current_user_id()


def get_async_current_cluster_id() -> Optional[str]:
    """
    Get the current cluster ID in async context.

    Returns:
        The current cluster ID or None if no cluster is selected
    """
    return get_current_cluster_id()
