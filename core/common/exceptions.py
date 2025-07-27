"""
Custom exceptions for ClustR application.

This module defines all custom exceptions used throughout the ClustR application.
Each exception has a specific error code, status code, and default message.
"""

from rest_framework import status
from rest_framework.exceptions import APIException

from core.common.error_codes import CommonAPIErrorCodes


class ClustRBaseException(APIException):
    """
    Base exception for all ClustR exceptions.
    
    All custom exceptions should inherit from this class to ensure consistent
    error handling and response formatting.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An unexpected error occurred."
    default_code = CommonAPIErrorCodes.INTERNAL_SERVER_ERROR


class InvalidDataException(ClustRBaseException):
    """
    Exception raised when invalid data is provided.

    This exception should be used when input data is invalid or does not meet
    the required criteria.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid data provided."
    default_code = CommonAPIErrorCodes.INVALID_INPUT

class UnprocessedEntityException(ClustRBaseException):
    """
    Exception raised when an entity cannot be processed.

    This exception should be used when an entity cannot be processed due to
    some business logic or validation error.
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Unable to process the entity."
    default_code = CommonAPIErrorCodes.BUSINESS_LOGIC_ERROR

class ValidationException(ClustRBaseException):
    """
    Exception raised when validation fails.
    
    This exception should be used when input data fails validation checks.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation failed."
    default_code = CommonAPIErrorCodes.VALIDATION_ERROR


class AuthenticationException(ClustRBaseException):
    """
    Exception raised when authentication fails.
    
    This exception should be used for authentication failures such as
    invalid credentials or expired tokens.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = CommonAPIErrorCodes.AUTHENTICATION_ERROR


class AuthorizationException(ClustRBaseException):
    """
    Exception raised when authorization fails.
    
    This exception should be used when a user does not have the required
    permissions to perform an action.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = CommonAPIErrorCodes.AUTHORIZATION_ERROR


class ResourceNotFoundException(ClustRBaseException):
    """
    Exception raised when a resource is not found.
    
    This exception should be used when a requested resource does not exist.
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = CommonAPIErrorCodes.RESOURCE_NOT_FOUND


class ResourceConflictException(ClustRBaseException):
    """
    Exception raised when a resource conflict occurs.
    
    This exception should be used when there is a conflict with the requested
    resource, such as a duplicate entry.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with the requested resource."
    default_code = CommonAPIErrorCodes.RESOURCE_CONFLICT


class DuplicateEntityException(ResourceConflictException):
    """
    Exception raised when a duplicate entity is detected.
    
    This exception should be used when attempting to create an entity that
    already exists.
    """
    default_detail = "The entity already exists."
    default_code = CommonAPIErrorCodes.DUPLICATE_ENTITY


class PaymentException(ClustRBaseException):
    """
    Exception raised when a payment operation fails.
    
    This exception should be used for general payment processing errors.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Payment operation failed."
    default_code = CommonAPIErrorCodes.PAYMENT_ERROR


class InsufficientFundsException(PaymentException):
    """
    Exception raised when there are insufficient funds for a payment.
    
    This exception should be used when a user does not have enough funds
    to complete a payment.
    """
    default_detail = "Insufficient funds to complete the payment."
    default_code = CommonAPIErrorCodes.INSUFFICIENT_FUNDS


class PaymentGatewayException(PaymentException):
    """
    Exception raised when a payment gateway operation fails.
    
    This exception should be used when there is an error with the payment
    gateway service.
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Payment gateway error."
    default_code = CommonAPIErrorCodes.PAYMENT_GATEWAY_ERROR


class ExternalServiceException(ClustRBaseException):
    """
    Exception raised when an external service call fails.
    
    This exception should be used when there is an error with an external
    service integration.
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service call failed."
    default_code = CommonAPIErrorCodes.EXTERNAL_SERVICE_ERROR


class ServiceUnavailableException(ExternalServiceException):
    """
    Exception raised when an external service is unavailable.
    
    This exception should be used when an external service is temporarily
    unavailable.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service is temporarily unavailable."
    default_code = CommonAPIErrorCodes.SERVICE_UNAVAILABLE


class ClusterAccessException(ClustRBaseException):
    """
    Exception raised when a user tries to access a cluster they don't have access to.
    
    This exception should be used when a user attempts to access data or
    functionality for a cluster they are not authorized to access.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to this cluster."
    default_code = CommonAPIErrorCodes.CLUSTER_ACCESS_DENIED


class ClusterNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a cluster is not found.
    
    This exception should be used when a requested cluster does not exist.
    """
    default_detail = "The requested cluster was not found."
    default_code = CommonAPIErrorCodes.CLUSTER_NOT_FOUND


class RateLimitException(ClustRBaseException):
    """
    Exception raised when rate limit is exceeded.
    
    This exception should be used when a user exceeds the rate limit for
    API requests.
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded."
    default_code = CommonAPIErrorCodes.RATE_LIMIT_EXCEEDED


class FileUploadException(ClustRBaseException):
    """
    Exception raised when a file upload fails.
    
    This exception should be used for general file upload errors.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "File upload failed."
    default_code = CommonAPIErrorCodes.FILE_UPLOAD_ERROR


class FileSizeExceededException(FileUploadException):
    """
    Exception raised when a file size exceeds the allowed limit.
    
    This exception should be used when a file is too large to upload.
    """
    default_detail = "File size exceeds the allowed limit."
    default_code = CommonAPIErrorCodes.FILE_SIZE_EXCEEDED


class InvalidFileTypeException(FileUploadException):
    """
    Exception raised when a file type is not allowed.
    
    This exception should be used when a file type is not supported.
    """
    default_detail = "File type is not allowed."
    default_code = CommonAPIErrorCodes.INVALID_FILE_TYPE


class BusinessLogicException(ClustRBaseException):
    """
    Exception raised when a business logic rule is violated.
    
    This exception should be used when a business rule or constraint is
    violated.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Business logic error."
    default_code = CommonAPIErrorCodes.BUSINESS_LOGIC_ERROR


class OperationNotAllowedException(BusinessLogicException):
    """
    Exception raised when an operation is not allowed.
    
    This exception should be used when an operation is not allowed due to
    business rules or constraints.
    """
    default_detail = "Operation not allowed."
    default_code = CommonAPIErrorCodes.OPERATION_NOT_ALLOWED


class FeatureDisabledException(BusinessLogicException):
    """
    Exception raised when a feature is disabled.
    
    This exception should be used when a user attempts to use a feature
    that is currently disabled.
    """
    default_detail = "This feature is currently disabled."
    default_code = CommonAPIErrorCodes.FEATURE_DISABLED


class DatabaseException(ClustRBaseException):
    """
    Exception raised when a database operation fails.
    
    This exception should be used for database-related errors.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Database operation failed."
    default_code = CommonAPIErrorCodes.DATABASE_ERROR