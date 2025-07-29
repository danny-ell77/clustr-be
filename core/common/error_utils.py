"""
Error handling utilities for ClustR application.

This module provides utility functions for error handling, including:
- Exception wrapping
- Error logging
- Error response generation
"""

import functools
import logging
import traceback
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from rest_framework.request import Request
from rest_framework.response import Response

from core.common.error_codes import CommonAPIErrorCodes
from core.common.exceptions import (
    ClustRBaseException,
    DatabaseException,
)
from core.common.logging import get_request_logger, log_audit
from core.common.middleware.request_middleware import (
    get_current_request,
    get_current_user_id,
    get_current_cluster_id,
)
from core.common.responses import (
    error_response,
    validation_error_response,
    permission_denied_response,
    not_found_response,
    authentication_error_response,
)

# Configure logger
logger = logging.getLogger("clustr")

# Type variable for function return type
T = TypeVar("T")


def log_exceptions(
    exception_mapping: Optional[
        dict[Type[Exception], Type[ClustRBaseException]]
    ] = None,
    log_level: int = logging.ERROR,
    reraise: bool = True,
) -> Callable:
    """
    Decorator to handle exceptions in a consistent way.

    Args:
        exception_mapping: Mapping of exception types to ClustR exception types
        log_level: The log level to use for exceptions
        reraise: Whether to reraise the exception after handling

    Returns:
        A decorator function
    """
    if exception_mapping is None:
        exception_mapping = {}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except tuple(exception_mapping.keys()) as exc:
                # Get the corresponding ClustR exception class
                clustr_exception_class = exception_mapping.get(type(exc))

                # Log the exception
                log_exception_with_context(exc, log_level=log_level)

                # Raise the mapped exception if available
                if clustr_exception_class:
                    raise clustr_exception_class(str(exc)) from exc

                # Reraise the original exception if requested
                if reraise:
                    raise

                # Return None if not reraising
                return cast(T, None)

        return wrapper

    return decorator


def log_exception_with_context(
    exc: Exception,
    log_level: int = logging.ERROR,
    request: Optional[HttpRequest] = None,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log an exception with context.

    Args:
        exc: The exception to log
        log_level: The log level to use
        request: The request object
        context: Additional context information
    """
    # Get the current request if not provided
    if request is None:
        request = get_current_request()

    # Get a logger with request context if available
    if request:
        log = get_request_logger(request)
    else:
        log = logger

    # Build the log message
    message = f"Exception: {exc.__class__.__name__}: {str(exc)}"

    # Build extra context
    extra = {
        "exception_type": exc.__class__.__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc(),
    }

    # Add user and cluster context if available
    user_id = get_current_user_id()
    if user_id:
        extra["user_id"] = user_id

    cluster_id = get_current_cluster_id()
    if cluster_id:
        extra["cluster_id"] = cluster_id

    # Add additional context if provided
    if context:
        extra.update(context)

    # Log the exception
    log.log(log_level, message, extra=extra)


def exception_to_response_mapper(
    exception_mapping: Optional[dict[Type[Exception], Union[Callable, Response]]] = None,
    log_exceptions: bool = True,
    default_response: Optional[Union[Callable, Response]] = None
) -> Callable:
    """
    Decorator that maps exceptions to response functions or Response objects to be used for function views.
    
    Args:
        exception_mapping: dict mapping exception types to response functions or Response objects
        log_exceptions: Whether to log caught exceptions
        default_response: Default response function/object for unmapped exceptions
        
    Returns:
        A decorator function
        
    Usage:
        @exception_to_response_mapper({
            ValueError: validation_error_response,
            PermissionError: permission_denied_response,
            CustomException: lambda exc: error_response("CUSTOM_ERROR", str(exc), 400)
        })
        def my_view(request):
            # Your view logic here
            pass
    """
    if exception_mapping is None:
        exception_mapping = {}
    
    # Default exception mappings
    default_mappings = {
        ValueError: lambda exc: error_response(
            CommonAPIErrorCodes.VALIDATION_ERROR,
            str(exc),
            status_code=400
        ),
        PermissionError: lambda exc: error_response(
            CommonAPIErrorCodes.PERMISSION_DENIED,
            str(exc),
            status_code=403
        ),
        FileNotFoundError: lambda exc: error_response(
            CommonAPIErrorCodes.RESOURCE_NOT_FOUND,
            str(exc),
            status_code=404
        ),
    }
    
    # Merge default mappings with user-provided mappings
    final_mapping = {**default_mappings, **exception_mapping}
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(request: Request, *args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Log the exception if requested
                if log_exceptions:
                    log_exception_with_context(exc, request=request)
                
                # Handle ClustR exceptions first
                if isinstance(exc, ClustRBaseException):
                    return error_response(
                        error_code=exc.default_code,
                        message=str(exc),
                        status_code=exc.status_code
                    )
                
                # Check for mapped exceptions
                for exception_type, response_handler in final_mapping.items():
                    if isinstance(exc, exception_type):
                        if callable(response_handler):
                            return response_handler(exc)
                        else:
                            return response_handler
                
                # Use default response if provided
                if default_response:
                    if callable(default_response):
                        return default_response(exc)
                    else:
                        return default_response
                
                # Fallback to internal server error
                return error_response(
                    error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                    message="An unexpected error occurred.",
                    details=str(exc) if settings.DEBUG else None,
                    status_code=500,
                )
        
        return wrapper
    
    return decorator


def audit_log(
    event_type: str,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[Callable[..., Optional[str]]] = None,
) -> Callable:
    """
    Decorator to log audit events.

    Args:
        event_type: The type of event (e.g., 'user.login', 'payment.create')
        resource_type: The type of resource affected (e.g., 'user', 'payment')
        get_resource_id: Function to extract the resource ID from function arguments

    Returns:
        A decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get the resource ID if a function is provided
            resource_id = None
            if get_resource_id:
                resource_id = get_resource_id(*args, **kwargs)

            # Get user and cluster IDs
            user_id = get_current_user_id()
            cluster_id = get_current_cluster_id()

            # Execute the function
            try:
                result = func(*args, **kwargs)

                # Log the audit event
                log_audit(
                    event_type=event_type,
                    user_id=user_id,
                    cluster_id=cluster_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={"status": "success"},
                )

                return result
            except Exception as exc:
                # Log the audit event with failure status
                log_audit(
                    event_type=event_type,
                    user_id=user_id,
                    cluster_id=cluster_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={
                        "status": "failure",
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    },
                )

                # Reraise the exception
                raise

        return wrapper

    return decorator
