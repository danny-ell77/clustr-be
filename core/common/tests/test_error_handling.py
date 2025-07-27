"""
Tests for the error handling framework.
"""

import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView
from rest_framework.response import Response

from core.common.error_codes import CommonAPIErrorCodes
from core.common.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    AuthorizationException,
    PaymentException,
)
from core.common.exception_handlers import custom_exception_handler
from core.common.middleware.exception_middleware import ExceptionMiddleware
from core.common.responses import (
    error_response,
    validation_error_response,
    not_found_response,
)
from core.common.error_utils import (
    log_exceptions,
    ErrorHandlingMixin,
    transactional,
)


class TestErrorResponse(TestCase):
    """Test the error response functions."""
    
    def test_error_response(self):
        """Test the error_response function."""
        response = error_response(
            CommonAPIErrorCodes.VALIDATION_ERROR,
            "Validation failed",
            {"field": "error"},
            status.HTTP_400_BAD_REQUEST
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.VALIDATION_ERROR)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertEqual(response.data["details"], {"field": "error"})
    
    def test_validation_error_response(self):
        """Test the validation_error_response function."""
        response = validation_error_response(
            "Custom validation error",
            {"field": "error"}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.VALIDATION_ERROR)
        self.assertEqual(response.data["message"], "Custom validation error")
        self.assertEqual(response.data["details"], {"field": "error"})
    
    def test_not_found_response(self):
        """Test the not_found_response function."""
        response = not_found_response(
            "Custom not found error",
            {"id": "123"}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.RESOURCE_NOT_FOUND)
        self.assertEqual(response.data["message"], "Custom not found error")
        self.assertEqual(response.data["details"], {"id": "123"})


class TestExceptionHandler(APITestCase):
    """Test the custom exception handler."""
    
    def test_validation_exception(self):
        """Test handling of ValidationException."""
        exc = ValidationException("Invalid data")
        response = custom_exception_handler(exc, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.VALIDATION_ERROR)
        self.assertEqual(response.data["message"], "Invalid data")
    
    def test_resource_not_found_exception(self):
        """Test handling of ResourceNotFoundException."""
        exc = ResourceNotFoundException("Resource not found")
        response = custom_exception_handler(exc, {})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.RESOURCE_NOT_FOUND)
        self.assertEqual(response.data["message"], "Resource not found")
    
    def test_authorization_exception(self):
        """Test handling of AuthorizationException."""
        exc = AuthorizationException("Not authorized")
        response = custom_exception_handler(exc, {})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.AUTHORIZATION_ERROR)
        self.assertEqual(response.data["message"], "Not authorized")


class TestExceptionMiddleware(TestCase):
    """Test the exception middleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ExceptionMiddleware(get_response=lambda r: None)
    
    def test_api_exception_handling(self):
        """Test handling of API exceptions."""
        request = self.factory.get("/api/test")
        exception = ValidationException("Invalid data")
        
        with patch("logging.Logger.exception") as mock_log:
            response = self.middleware.process_exception(request, exception)
            
            self.assertTrue(mock_log.called)
            self.assertIsInstance(response, JsonResponse)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            
            data = json.loads(response.content)
            self.assertEqual(data["error"], CommonAPIErrorCodes.VALIDATION_ERROR)
            self.assertEqual(data["message"], "Invalid data")
    
    def test_non_api_request(self):
        """Test that non-API requests are not handled."""
        request = self.factory.get("/non-api/test")
        exception = Exception("Generic error")
        
        response = self.middleware.process_exception(request, exception)
        self.assertIsNone(response)


class TestErrorHandlingDecorators(TestCase):
    """Test the error handling decorators."""
    
    def test_log_exceptions_decorator(self):
        """Test the log_exceptions decorator."""
        exception_mapping = {
            ValueError: ValidationException,
            KeyError: ResourceNotFoundException,
        }
        
        @log_exceptions(exception_mapping=exception_mapping)
        def function_with_value_error():
            raise ValueError("Invalid value")
        
        @log_exceptions(exception_mapping=exception_mapping)
        def function_with_key_error():
            raise KeyError("Missing key")
        
        with self.assertRaises(ValidationException):
            function_with_value_error()
        
        with self.assertRaises(ResourceNotFoundException):
            function_with_key_error()
    
    def test_transactional_decorator(self):
        """Test the transactional decorator."""
        @transactional
        def function_with_exception():
            raise ValueError("Test exception")
        
        with patch("django.db.transaction.atomic") as mock_atomic:
            mock_atomic.return_value.__enter__ = MagicMock()
            mock_atomic.return_value.__exit__ = MagicMock()
            
            with self.assertRaises(ValueError):
                function_with_exception()
            
            self.assertTrue(mock_atomic.called)


class TestErrorHandlingMixin(APITestCase):
    """Test the ErrorHandlingMixin."""
    
    class TestView(ErrorHandlingMixin, APIView):
        def get(self, request):
            raise ValidationException("Test validation error")
    
    def test_error_handling_mixin(self):
        """Test that the mixin handles exceptions correctly."""
        factory = APIRequestFactory()
        view = self.TestView.as_view()
        request = factory.get("/test")
        response = view(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], CommonAPIErrorCodes.VALIDATION_ERROR)
        self.assertEqual(response.data["message"], "Test validation error")