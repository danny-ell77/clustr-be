"""
Custom exception handlers for ClustR application.

This module provides a custom exception handler for Django REST Framework
that ensures consistent error response formatting across the application.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db.utils import DatabaseError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException, 
    AuthenticationFailed, 
    NotAuthenticated, 
    ParseError,
    MethodNotAllowed,
    NotFound,
    PermissionDenied as DRFPermissionDenied,
    ValidationError as DRFValidationError,
    Throttled
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.common.error_codes import CommonAPIErrorCodes

# Configure logger
logger = logging.getLogger("clustr")


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Optional[Response]:
    """
    Custom exception handler for REST framework that formats the response consistently.
    
    1. Get request information for logging
    2. Call REST framework's default exception handler first
    3. If this is a Django exception that wasn't handled by DRF
    4. Unhandled exceptions should be logged with full traceback
    
    Args:
        exc: The exception that was raised
        context: The context of the exception
        
    Returns:
        A formatted Response object or None if the exception cannot be handled
    """
    request = context.get('request')
    request_info = ""
    if request:
        request_info = f"{request.method} {request.path}"
    
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, Http404):
            logger.info(f"Resource not found: {request_info}")
            data = {
                "error": CommonAPIErrorCodes.RESOURCE_NOT_FOUND,
                "message": "The requested resource was not found.",
                "details": str(exc),
            }
            response = Response(data, status=status.HTTP_404_NOT_FOUND)
        
        elif isinstance(exc, PermissionDenied):
            logger.warning(f"Permission denied: {request_info}")
            data = {
                "error": CommonAPIErrorCodes.PERMISSION_DENIED,
                "message": "You do not have permission to perform this action.",
                "details": str(exc),
            }
            response = Response(data, status=status.HTTP_403_FORBIDDEN)
        
        elif isinstance(exc, DjangoValidationError):
            logger.info(f"Validation error: {request_info}")
            data = {
                "error": CommonAPIErrorCodes.VALIDATION_ERROR,
                "message": "Validation failed.",
                "details": exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            }
            response = Response(data, status=status.HTTP_400_BAD_REQUEST)
        
        elif isinstance(exc, DatabaseError):
            logger.error(f"Database error: {request_info}", exc_info=exc)
            data = {
                "error": CommonAPIErrorCodes.DATABASE_ERROR,
                "message": "A database error occurred.",
                "details": str(exc) if settings.DEBUG else "Please contact support.",
            }
            response = Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            logger.error(
                f"Unhandled exception in {request_info}: {exc.__class__.__name__}",
                exc_info=exc
            )
            
            # In production, don't expose internal error details
            error_details = "Please contact support."
            if settings.DEBUG:
                error_details = {
                    "exception": str(exc),
                    "traceback": traceback.format_exc().split('\n'),
                }
            
            data = {
                "error": CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "An unexpected error occurred.",
                "details": error_details,
            }
            response = Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        data = response.data
        error_code = _get_error_code(exc)
        
        _log_exception(exc, error_code, request_info)
        
        formatted_data = {
            "error": error_code,
            "message": _get_error_message(exc, data),
            "details": _get_error_details(data),
        }
        
        if formatted_data["details"] is None:
            del formatted_data["details"]
            
        response.data = formatted_data

    return response


def _get_error_code(exc: Exception) -> str:
    """
    Get the error code for an exception.
    
    Args:
        exc: The exception to get the error code for
        
    Returns:
        A string representing the error code
    """
    # Handle DRF built-in exceptions
    if isinstance(exc, AuthenticationFailed) or isinstance(exc, NotAuthenticated):
        return CommonAPIErrorCodes.AUTHENTICATION_ERROR
    elif isinstance(exc, DRFPermissionDenied):
        return CommonAPIErrorCodes.AUTHORIZATION_ERROR
    elif isinstance(exc, NotFound):
        return CommonAPIErrorCodes.RESOURCE_NOT_FOUND
    elif isinstance(exc, ParseError):
        return CommonAPIErrorCodes.VALIDATION_ERROR
    elif isinstance(exc, MethodNotAllowed):
        return CommonAPIErrorCodes.OPERATION_NOT_ALLOWED
    elif isinstance(exc, Throttled):
        return CommonAPIErrorCodes.RATE_LIMIT_EXCEEDED
    elif isinstance(exc, DRFValidationError):
        return CommonAPIErrorCodes.VALIDATION_ERROR
    
    # Handle custom exceptions
    elif hasattr(exc, "default_code") and exc.default_code:
        return exc.default_code
    elif hasattr(exc, "code") and exc.code:
        return exc.code
    
    # Default case
    else:
        return CommonAPIErrorCodes.INTERNAL_SERVER_ERROR


def _get_error_message(exc: Exception, data: dict[str, Any]) -> str:
    """
    Get a human-readable error message.
    
    Args:
        exc: The exception
        data: The response data
        
    Returns:
        A string containing the error message
    """
    if hasattr(exc, "detail") and isinstance(exc.detail, str):
        return exc.detail
    elif isinstance(data, dict) and "detail" in data and isinstance(data["detail"], str):
        return data["detail"]
    elif hasattr(exc, "message"):
        return exc.message
    else:
        return str(exc)


def _get_error_details(data: dict[str, Any]) -> Union[dict[str, Any], str, None]:
    """
    Extract detailed error information.
    
    Args:
        data: The response data
        
    Returns:
        Detailed error information or None if no details are available
    """
    if isinstance(data, dict):
        # Remove the detail field if it exists and is a string
        if "detail" in data and isinstance(data["detail"], str):
            data_copy = data.copy()
            del data_copy["detail"]
            if data_copy:
                return data_copy
            return None
        return data
    elif isinstance(data, list):
        return {"errors": data}
    else:
        return None


def _log_exception(exc: Exception, error_code: str, request_info: str) -> None:
    """
    Log an exception with appropriate severity based on the error code.
    
    Args:
        exc: The exception to log
        error_code: The error code
        request_info: Information about the request
    """
    # Determine log level based on error code
    if error_code in [
        CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
        CommonAPIErrorCodes.DATABASE_ERROR,
        CommonAPIErrorCodes.EXTERNAL_SERVICE_ERROR,
        CommonAPIErrorCodes.SERVICE_UNAVAILABLE
    ]:
        logger.error(f"{error_code} in {request_info}: {exc.__class__.__name__}", exc_info=exc)
    
    elif error_code in [
        CommonAPIErrorCodes.AUTHENTICATION_ERROR,
        CommonAPIErrorCodes.AUTHORIZATION_ERROR,
        CommonAPIErrorCodes.PERMISSION_DENIED,
        CommonAPIErrorCodes.PAYMENT_ERROR,
        CommonAPIErrorCodes.PAYMENT_GATEWAY_ERROR
    ]:
        logger.warning(f"{error_code} in {request_info}: {exc}")
    
    else:
        # For validation errors, not found, etc.
        logger.info(f"{error_code} in {request_info}: {exc}")