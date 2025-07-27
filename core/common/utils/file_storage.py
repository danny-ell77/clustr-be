"""
File storage utilities for ClustR application.
"""

import os
import uuid
from datetime import datetime
from typing import BinaryIO, Dict, Union

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from core.common.exceptions import FileSizeExceededException


class FileStorage:
    """
    Utility class for handling file storage operations.
    Supports both local and cloud storage backends.
    """
    
    ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']
    ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv', 'ppt', 'pptx']
    ALLOWED_MEDIA_EXTENSIONS = ['mp3', 'mp4', 'wav', 'avi', 'mov', 'wmv', 'flv', 'mkv']
    
    # Maximum file sizes (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def get_file_extension(cls, filename: str) -> str:
        """Get the file extension from a filename."""
        return filename.split('.')[-1].lower() if '.' in filename else ''
    
    @classmethod
    def is_valid_image(cls, filename: str) -> bool:
        """Check if the file is a valid image based on extension."""
        return cls.get_file_extension(filename) in cls.ALLOWED_IMAGE_EXTENSIONS
    
    @classmethod
    def is_valid_document(cls, filename: str) -> bool:
        """Check if the file is a valid document based on extension."""
        return cls.get_file_extension(filename) in cls.ALLOWED_DOCUMENT_EXTENSIONS
    
    @classmethod
    def is_valid_media(cls, filename: str) -> bool:
        """Check if the file is a valid media file based on extension."""
        return cls.get_file_extension(filename) in cls.ALLOWED_MEDIA_EXTENSIONS
    
    @classmethod
    def validate_file_size(cls, file_size: int, filename: str) -> bool:
        """
        Validate file size based on file type.
        
        Args:
            file_size: Size of the file in bytes
            filename: Name of the file
            
        Returns:
            True if file size is valid, False otherwise
        """
        if cls.is_valid_image(filename):
            return file_size <= cls.MAX_IMAGE_SIZE
        elif cls.is_valid_document(filename):
            return file_size <= cls.MAX_DOCUMENT_SIZE
        elif cls.is_valid_media(filename):
            return file_size <= cls.MAX_MEDIA_SIZE
        else:
            # Default to document size limit for unknown types
            return file_size <= cls.MAX_DOCUMENT_SIZE
    
    @classmethod
    def get_file_type_category(cls, filename: str) -> str:
        """
        Get the category of file based on extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Category of the file ('image', 'document', 'media', 'other')
        """
        if cls.is_valid_image(filename):
            return 'image'
        elif cls.is_valid_document(filename):
            return 'document'
        elif cls.is_valid_media(filename):
            return 'media'
        else:
            return 'other'
    
    @classmethod
    def generate_unique_filename(cls, original_filename: str) -> str:
        """Generate a unique filename to prevent collisions."""
        # Get the file extension
        ext = cls.get_file_extension(original_filename)
        
        # Generate a unique filename using UUID
        unique_name = f"{uuid.uuid4().hex}"
        
        # Add the extension if it exists
        if ext:
            return f"{unique_name}.{ext}"
        return unique_name
    
    @classmethod
    def get_storage_path(cls, filename: str, folder: str = None, cluster_id: str = None) -> str:
        """
        Generate a storage path for the file.
        
        Args:
            filename: The original filename
            folder: Optional folder name (e.g., 'profiles', 'documents')
            cluster_id: Optional cluster ID for multi-tenant isolation
            
        Returns:
            A storage path for the file
        """
        # Start with the base path
        path_parts = []
        
        # Add cluster_id for multi-tenant isolation if provided
        if cluster_id:
            path_parts.append(f"clusters/{cluster_id}")
        
        # Add folder if provided
        if folder:
            path_parts.append(folder)
        
        # Add date-based path for better organization
        today = datetime.now()
        path_parts.append(f"{today.year}/{today.month:02d}/{today.day:02d}")
        
        # Join the path parts
        path = '/'.join(path_parts)
        
        # Generate a unique filename
        unique_filename = cls.generate_unique_filename(filename)
        
        # Return the full path
        return f"{path}/{unique_filename}"
    
    @classmethod
    def save_file(cls, file_content: BinaryIO, filename: str, folder: str = None, 
                  cluster_id: str = None, content_type: str = None) -> str:
        """
        Save a file to storage.
        
        Args:
            file_content: The file content as a file-like object
            filename: The original filename
            folder: Optional folder name
            cluster_id: Optional cluster ID for multi-tenant isolation
            content_type: Optional content type of the file
            
        Returns:
            The storage path where the file was saved
        """
        # Generate a storage path
        storage_path = cls.get_storage_path(filename, folder, cluster_id)
        
        # Save the file using the default storage backend
        default_storage.save(storage_path, ContentFile(file_content.read()))
        
        return storage_path
    
    @classmethod
    def get_file_url(cls, file_path: str, expires: int = None) -> str:
        """
        Get a URL for accessing the file.
        
        Args:
            file_path: The storage path of the file
            expires: Optional expiration time in seconds
            
        Returns:
            A URL for accessing the file
        """
        # For cloud storage like S3, generate a signed URL if expiration is provided
        if hasattr(default_storage, 'url') and expires is not None and hasattr(default_storage, 'generate_presigned_url'):
            # This is for S3Boto3Storage or similar
            return default_storage.generate_presigned_url(file_path, expires)
        
        # For standard storage, just return the URL
        return default_storage.url(file_path)
    
    @classmethod
    def delete_file(cls, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: The storage path of the file
            
        Returns:
            True if the file was deleted, False otherwise
        """
        if default_storage.exists(file_path):
            default_storage.delete(file_path)
            return True
        return False
    
    @classmethod
    def get_file_metadata(cls, file_path: str) -> Dict[str, Union[str, int, datetime]]:
        """
        Get metadata for a file.
        
        Args:
            file_path: The storage path of the file
            
        Returns:
            A dictionary containing file metadata
        """
        if not default_storage.exists(file_path):
            return {}
        
        # Get file info
        file_info = {}
        
        # Get file size
        try:
            file_info['size'] = default_storage.size(file_path)
        except NotImplementedError:
            file_info['size'] = 0
        
        # Get last modified time
        try:
            file_info['modified'] = default_storage.get_modified_time(file_path)
        except NotImplementedError:
            file_info['modified'] = None
        
        # Get file extension
        file_info['extension'] = cls.get_file_extension(file_path)
        
        # Get file name
        file_info['name'] = os.path.basename(file_path)
        
        return file_info
    
    @classmethod
    def upload_file(cls, file_obj, folder: str = None, cluster_id: str = None) -> str:
        """
        Upload a file and return its URL.
        
        Args:
            file_obj: The uploaded file object
            folder: Optional folder name
            cluster_id: Optional cluster ID for multi-tenant isolation
            
        Returns:
            The URL of the uploaded file
        """
        # Validate file size
        if not cls.validate_file_size(file_obj.size, file_obj.name):
            raise FileSizeExceededException()
        
        # Save the file
        storage_path = cls.save_file(
            file_obj,
            file_obj.name,
            folder=folder,
            cluster_id=cluster_id,
            content_type=file_obj.content_type
        )
        
        # Return the URL
        return cls.get_file_url(storage_path)