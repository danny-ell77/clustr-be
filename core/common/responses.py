"""
Standard response helpers for ClustR application.

This module provides helper functions for creating consistent API responses
throughout the application, particularly for error cases.
"""

from typing import Any, Dict, List, Optional, Union

from rest_framework import status
from rest_framework.response import Response

from core.common.error_codes import CommonAPIErrorCodes


def error_response(
    error_code: str,
    message: str,
    details: Optional[Union[dict[str, Any], List[Any], str]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """
    Create a standardized error response.
    
    Args:
        error_code: The error code
        message: A human-readable error message
        details: Optional additional error details
        status_code: The HTTP status code
        
    Returns:
        A Response object with standardized error format
    """
    response_data = {
        "error": error_code,
        "message": message,
    }
    
    if details is not None:
        response_data["details"] = details
        
    return Response(response_data, status=status_code)


def validation_error_response(
    message: str = "Validation failed.",
    details: Optional[dict[str, Any]] = None
) -> Response:
    """
    Create a validation error response.
    
    Args:
        message: A human-readable error message
        details: Validation error details
        
    Returns:
        A Response object with validation error format
    """
    return error_response(
        CommonAPIErrorCodes.VALIDATION_ERROR,
        message,
        details,
        status.HTTP_400_BAD_REQUEST
    )


def not_found_response(
    message: str = "The requested resource was not found.",
    details: Optional[Any] = None
) -> Response:
    """
    Create a not found error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the missing resource
        
    Returns:
        A Response object with not found error format
    """
    return error_response(
        CommonAPIErrorCodes.RESOURCE_NOT_FOUND,
        message,
        details,
        status.HTTP_404_NOT_FOUND
    )


def permission_denied_response(
    message: str = "You do not have permission to perform this action.",
    details: Optional[Any] = None
) -> Response:
    """
    Create a permission denied error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the permission issue
        
    Returns:
        A Response object with permission denied error format
    """
    return error_response(
        CommonAPIErrorCodes.PERMISSION_DENIED,
        message,
        details,
        status.HTTP_403_FORBIDDEN
    )


def authentication_error_response(
    message: str = "Authentication failed.",
    details: Optional[Any] = None
) -> Response:
    """
    Create an authentication error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the authentication issue
        
    Returns:
        A Response object with authentication error format
    """
    return error_response(
        CommonAPIErrorCodes.AUTHENTICATION_ERROR,
        message,
        details,
        status.HTTP_401_UNAUTHORIZED
    )


def duplicate_entity_response(
    message: str = "The entity already exists.",
    details: Optional[Any] = None
) -> Response:
    """
    Create a duplicate entity error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the duplicate entity
        
    Returns:
        A Response object with duplicate entity error format
    """
    return error_response(
        CommonAPIErrorCodes.DUPLICATE_ENTITY,
        message,
        details,
        status.HTTP_409_CONFLICT
    )


def payment_error_response(
    message: str = "Payment operation failed.",
    details: Optional[Any] = None
) -> Response:
    """
    Create a payment error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the payment issue
        
    Returns:
        A Response object with payment error format
    """
    return error_response(
        CommonAPIErrorCodes.PAYMENT_ERROR,
        message,
        details,
        status.HTTP_400_BAD_REQUEST
    )


def external_service_error_response(
    message: str = "External service call failed.",
    details: Optional[Any] = None
) -> Response:
    """
    Create an external service error response.
    
    Args:
        message: A human-readable error message
        details: Additional details about the external service issue
        
    Returns:
        A Response object with external service error format
    """
    return error_response(
        CommonAPIErrorCodes.EXTERNAL_SERVICE_ERROR,
        message,
        details,
        status.HTTP_502_BAD_GATEWAY
    )


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """
    Create a standardized success response.
    
    Args:
        data: The response data
        message: An optional success message
        status_code: The HTTP status code
        
    Returns:
        A Response object with standardized success format
    """
    response_data = {}
    
    if data is not None:
        if isinstance(data, dict):
            response_data.update(data)
        else:
            response_data["data"] = data
            
    if message is not None:
        response_data["message"] = message
        
    return Response(response_data, status=status_code)


def created_response(
    data: Any = None,
    message: str = "Resource created successfully."
) -> Response:
    """
    Create a standardized created response.
    
    Args:
        data: The created resource data
        message: A success message
        
    Returns:
        A Response object with standardized created format
    """
    return success_response(data, message, status.HTTP_201_CREATED)


def no_content_response() -> Response:
    """
    Create a no content response.
    
    Returns:
        A Response object with no content
    """
    return Response(status=status.HTTP_204_NO_CONTENT)
