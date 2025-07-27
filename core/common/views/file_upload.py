"""
File upload views for ClustR application.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.db import transaction

from accounts.permissions import HasClusterPermission
from core.common.permissions import CommunicationsPermissions
from core.common.models import AnnouncementAttachment
from core.common.serializers.announcement_serializers import AnnouncementAttachmentSerializer
from core.common.utils.file_storage import FileStorage
from core.common.exceptions import InvalidFileTypeException


class FileUploadViewSet(viewsets.ViewSet):
    """
    ViewSet for handling file uploads.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def upload(self, request: Request) -> Response:
        """
        Upload a file.
        
        Args:
            request: The request object
            
        Returns:
            Response with the file URL
        """
        # Get the file from the request
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the folder from the request
        folder = request.data.get('folder', 'uploads')
        
        # Get the cluster context from the request
        cluster_id = None
        if hasattr(request, 'cluster_context') and request.cluster_context:
            cluster_id = str(request.cluster_context.id)
        
        # Save the file
        try:
            file_path = FileStorage.save_file(
                file_obj,
                file_obj.name,
                folder=folder,
                cluster_id=cluster_id,
                content_type=file_obj.content_type
            )
            
            # Get the file URL
            file_url = FileStorage.get_file_url(file_path)
            
            # Get file metadata
            file_metadata = FileStorage.get_file_metadata(file_path)
            
            return Response({
                'url': file_url,
                'path': file_path,
                'name': file_obj.name,
                'size': file_metadata.get('size', file_obj.size),
                'type': file_obj.content_type,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def delete(self, request: Request) -> Response:
        """
        Delete a file.
        
        Args:
            request: The request object
            
        Returns:
            Response indicating success or failure
        """
        # Get the file path from the request
        file_path = request.data.get('path')
        if not file_path:
            return Response(
                {'error': 'No file path provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete the file
        try:
            success = FileStorage.delete_file(file_path)
            if success:
                return Response(
                    {'message': 'File deleted successfully'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'File not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )    
    
    @action(detail=False, methods=['post'])
    def upload_announcement_attachment(self, request: Request) -> Response:
        """
        Upload an attachment for announcements.
        
        Args:
            request: The request object
            
        Returns:
            Response with the attachment details
        """
        # Get the file from the request
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type for announcements
        allowed_extensions = (
            FileStorage.ALLOWED_IMAGE_EXTENSIONS + 
            FileStorage.ALLOWED_DOCUMENT_EXTENSIONS
        )
        file_extension = FileStorage.get_file_extension(file_obj.name)
        
        if file_extension not in allowed_extensions:
            raise InvalidFileTypeException()
        
        # Validate file size
        if not FileStorage.validate_file_size(file_obj.size, file_obj.name):
            file_category = FileStorage.get_file_type_category(file_obj.name)
            max_size_mb = {
                'image': FileStorage.MAX_IMAGE_SIZE // (1024 * 1024),
                'document': FileStorage.MAX_DOCUMENT_SIZE // (1024 * 1024),
                'media': FileStorage.MAX_MEDIA_SIZE // (1024 * 1024),
            }.get(file_category, 10)
            
            return Response(
                {
                    'error': f'File size too large. Maximum allowed size for {file_category} files: {max_size_mb}MB'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the cluster context from the request
        cluster_id = None
        if hasattr(request, 'cluster_context') and request.cluster_context:
            cluster_id = str(request.cluster_context.id)
        
        # Save the file
        try:
            file_path = FileStorage.save_file(
                file_obj,
                file_obj.name,
                folder='announcements/attachments',
                cluster_id=cluster_id,
                content_type=file_obj.content_type
            )
            
            # Get the file URL
            file_url = FileStorage.get_file_url(file_path)
            
            # Create the attachment record (without linking to announcement yet)
            with transaction.atomic():
                attachment = AnnouncementAttachment.objects.create(
                    announcement=None,  # Will be linked when announcement is created
                    file_name=file_obj.name,
                    file_url=file_url,
                    file_size=file_obj.size,
                    file_type=file_obj.content_type or 'application/octet-stream',
                    is_image=FileStorage.is_valid_image(file_obj.name),
                )
            
            # Return attachment details
            serializer = AnnouncementAttachmentSerializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def preview_attachment(self, request: Request) -> Response:
        """
        Get preview information for an attachment.
        
        Args:
            request: The request object with attachment_id parameter
            
        Returns:
            Response with preview information
        """
        attachment_id = request.query_params.get('attachment_id')
        if not attachment_id:
            return Response(
                {'error': 'attachment_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = AnnouncementAttachment.objects.get(id=attachment_id)
        except AnnouncementAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate preview data
        preview_data = {
            'id': attachment.id,
            'file_name': attachment.file_name,
            'file_size': attachment.file_size,
            'file_type': attachment.file_type,
            'is_image': attachment.is_image,
            'file_url': attachment.file_url,
            'created_at': attachment.created_at,
        }
        
        # Add image-specific preview data
        if attachment.is_image:
            preview_data.update({
                'preview_type': 'image',
                'thumbnail_url': attachment.file_url,  # For now, use the same URL
                'can_preview': True,
            })
        # Add document-specific preview data
        elif FileStorage.is_valid_document(attachment.file_name):
            preview_data.update({
                'preview_type': 'document',
                'can_preview': attachment.file_type == 'application/pdf',  # Only PDFs can be previewed
                'download_url': attachment.file_url,
            })
        else:
            preview_data.update({
                'preview_type': 'file',
                'can_preview': False,
                'download_url': attachment.file_url,
            })
        
        return Response(preview_data)
    
    @action(detail=False, methods=['delete'])
    def delete_attachment(self, request: Request) -> Response:
        """
        Delete an announcement attachment.
        
        Args:
            request: The request object with attachment_id parameter
            
        Returns:
            Response indicating success or failure
        """
        attachment_id = request.data.get('attachment_id')
        if not attachment_id:
            return Response(
                {'error': 'attachment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = AnnouncementAttachment.objects.get(id=attachment_id)
        except AnnouncementAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if attachment is linked to an announcement
        if attachment.announcement:
            return Response(
                {'error': 'Cannot delete attachment that is linked to an announcement'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete the file from storage
        try:
            # Extract file path from URL (this might need adjustment based on storage backend)
            file_path = attachment.file_url.split('/')[-4:]  # Adjust based on URL structure
            file_path = '/'.join(file_path)
            FileStorage.delete_file(file_path)
        except Exception:
            # Continue with database deletion even if file deletion fails
            pass
        
        # Delete the attachment record
        attachment.delete()
        
        return Response(
            {'message': 'Attachment deleted successfully'},
            status=status.HTTP_200_OK
        )