"""
Enhanced profile management views for the members app.
"""

import logging
import uuid
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AccountUser, UserVerification, VerifyMode, VerifyReason
from core.common.error_utils import log_exception_with_context, audit_log
from core.common.exceptions import ValidationException

logger = logging.getLogger('clustr')


class ProfilePictureUploadView(APIView):
    """
    API endpoint for uploading profile pictures.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @audit_log(event_type='user.profile_picture_upload', resource_type='user')
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            raise ValidationException(_("No file provided."))
        
        file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            raise ValidationException(_("Invalid file type. Allowed types: JPEG, PNG, GIF."))
        
        # Validate file size
        max_size = getattr(settings, 'MAX_PROFILE_PICTURE_SIZE_MB', 5) * 1024 * 1024  # Convert MB to bytes
        if file.size > max_size:
            raise ValidationException(_("File too large. Maximum size: 5MB."))
        
        try:
            # Generate a unique filename
            filename = f"{uuid.uuid4()}-{file.name}"
            
            # Upload to storage
            url = self._upload_to_storage(file, filename)
            
            # Update user profile
            user = request.user
            user.profile_image_url = url
            user.save(update_fields=['profile_image_url'])
            
            return Response({
                "detail": _("Profile picture uploaded successfully."),
                "url": url
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise ValidationException(_("Failed to upload profile picture."))
    
    def _upload_to_storage(self, file, filename):
        """
        Upload a file to the configured storage backend.
        
        This is a placeholder implementation. In a real application, this would
        upload to S3, Azure Blob Storage, or another cloud storage service.
        
        Args:
            file: The file to upload
            filename: The filename to use
            
        Returns:
            The URL of the uploaded file
        """
        # For demonstration purposes, we'll just return a mock URL
        # In a real implementation, this would use Django's storage API
        
        # Example S3 implementation:
        # from django.core.files.storage import default_storage
        # path = default_storage.save(f'profile_pictures/{filename}', file)
        # return default_storage.url(path)
        
        # For now, return a mock URL
        return f"https://storage.clustr.app/profile_pictures/{filename}"


class RequestProfileUpdateVerificationView(APIView):
    """
    API endpoint to request verification for profile updates.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        verify_mode = request.data.get('mode', VerifyMode.OTP)
        
        # Generate verification token/OTP
        verification = UserVerification.for_mode(
            verify_mode, request.user, VerifyReason.PROFILE_UPDATE
        )
        verification.send_mail()
        
        return Response({
            "detail": _("Verification code sent to your email.")
        }, status=status.HTTP_200_OK)


class VerifyProfileUpdateView(APIView):
    """
    API endpoint to verify profile updates with OTP/token.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        verification_key = request.data.get('verification_key')
        
        if not verification_key:
            raise ValidationException(_("Verification key is required."))
        
        try:
            # Find verification record
            verification = self._get_verification(verification_key, request.user)
            
            if verification.is_expired:
                raise ValidationException(_("Verification code has expired. Please request a new one."))
            
            # Mark as verified
            with transaction.atomic():
                verification.is_used = True
                verification.save(update_fields=['is_used'])
            
            return Response({
                "detail": _("Profile update verified successfully.")
            }, status=status.HTTP_200_OK)
            
        except ValidationException:
            # Re-raise validation exceptions
            raise
        except Exception as e:
            log_exception_with_context(e, request=request)
            raise ValidationException(_("Failed to verify profile update."))
    
    def _get_verification(self, verification_key, user):
        """
        Get the verification record for the given key.
        
        Args:
            verification_key: The verification key (OTP or token)
            user: The user requesting verification
            
        Returns:
            The verification record
            
        Raises:
            ValidationException: If the verification key is invalid
        """
        # Try to find by OTP first (for short keys)
        if len(verification_key) <= UserVerification.OTP_MAX_LENGTH:
            verification = UserVerification.objects.filter(
                otp=verification_key,
                requested_by=user,
                is_used=False
            ).first()
        else:
            # For longer keys, try to unsign the token
            try:
                from django.core.signing import BadSignature
                from core.common.email_sender import NotificationTypes
                
                # Try to unsign the token
                token = UserVerification.unsign_token(
                    verification_key,
                    reason=NotificationTypes.PROFILE_UPDATE_TOKEN
                )
                
                verification = UserVerification.objects.filter(
                    token=token,
                    requested_by=user,
                    is_used=False
                ).first()
                
            except BadSignature:
                # If unsigning fails, try direct match as fallback
                verification = UserVerification.objects.filter(
                    token=verification_key,
                    requested_by=user,
                    is_used=False
                ).first()
        
        if not verification:
            raise ValidationException(_("Invalid verification key."))
            
        return verification