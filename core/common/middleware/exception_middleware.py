"""
Exception middleware for ClustR application.

This middleware handles exceptions that occur during request processing
and formats them into consistent JSON responses.
"""

import json
import logging
import traceback
from typing import Any, Callable, Dict, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.utils import DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from core.common.error_codes import CommonAPIErrorCodes

logger = logging.getLogger('clustr')


class ExceptionMiddleware(MiddlewareMixin):
    """
    Middleware to handle exceptions globally.
    
    This middleware catches exceptions that aren't handled by the DRF exception
    handler, such as exceptions raised in middleware or outside of views.
    """
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """
        Process an exception and return a JSON response.
        
        Args:
            request: The request object
            exception: The exception that was raised
            
        Returns:
            A JSON response with error details or None to let other middleware handle it
        """
        # For API requests, format the response as JSON
        if self._is_api_request(request):
            # Log the exception with request details
            logger.exception(
                f"Unhandled exception in {request.method} {request.path}",
                exc_info=exception
            )
            
            # Prepare the error response
            error_data = self._prepare_error_data(exception)
            
            # Return a JSON response
            return JsonResponse(
                error_data,
                status=error_data.get('status', 500)
            )
        
        # For non-API requests, let Django handle it
        return None
    
    def _is_api_request(self, request: HttpRequest) -> bool:
        """
        Determine if the request is an API request.
        
        Args:
            request: The request object
            
        Returns:
            True if the request is an API request, False otherwise
        """
        # Check if the request path starts with /api/
        if request.path.startswith('/api/'):
            return True
        
        # Check if the request accepts JSON
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'application/json' in accept_header:
            return True
        
        # Check if the request is an AJAX request
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return True
        
        return False
    
    def _prepare_error_data(self, exception: Exception) -> dict[str, Any]:
        """
        Prepare error data for the response.
        
        Args:
            exception: The exception that was raised
            
        Returns:
            A dictionary with error details
        """
        # Default error data
        error_data = {
            'error': CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
            'message': 'An unexpected error occurred.',
            'status': 500,
        }
        
        # Add details in debug mode
        if settings.DEBUG:
            error_data['details'] = {
                'exception': str(exception),
                'traceback': traceback.format_exc().split('\n'),
            }
        
        # Handle specific exception types
        if isinstance(exception, PermissionDenied):
            error_data['error'] = CommonAPIErrorCodes.PERMISSION_DENIED
            error_data['message'] = 'You do not have permission to perform this action.'
            error_data['status'] = 403
        
        elif isinstance(exception, ValidationError):
            error_data['error'] = CommonAPIErrorCodes.VALIDATION_ERROR
            error_data['message'] = 'Validation failed.'
            error_data['status'] = 400
            if hasattr(exception, 'message_dict'):
                error_data['details'] = exception.message_dict
        
        elif isinstance(exception, DatabaseError):
            error_data['error'] = CommonAPIErrorCodes.DATABASE_ERROR
            error_data['message'] = 'A database error occurred.'
            error_data['status'] = 500
        
        # Handle custom exceptions
        elif hasattr(exception, 'status_code'):
            error_data['status'] = exception.status_code
        
        if hasattr(exception, 'default_code'):
            error_data['error'] = exception.default_code
        
        if hasattr(exception, 'detail'):
            if isinstance(exception.detail, str):
                error_data['message'] = exception.detail
            elif isinstance(exception.detail, dict):
                error_data['message'] = 'Validation failed.'
                error_data['details'] = exception.detail
        
        return error_data