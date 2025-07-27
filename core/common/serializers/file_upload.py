"""
File upload serializers for ClustR application.
"""

from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file uploads.
    """
    file = serializers.FileField(required=True)
    folder = serializers.CharField(required=False, default='uploads')
    
    def validate_file(self, value):
        """
        Validate the file.
        """
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        return value


class FileDeleteSerializer(serializers.Serializer):
    """
    Serializer for file deletion.
    """
    path = serializers.CharField(required=True)


class FileResponseSerializer(serializers.Serializer):
    """
    Serializer for file upload response.
    """
    url = serializers.URLField()
    path = serializers.CharField()
    name = serializers.CharField()
    size = serializers.IntegerField()
    type = serializers.CharField()


class AttachmentPreviewSerializer(serializers.Serializer):
    """
    Serializer for attachment preview response.
    """
    id = serializers.UUIDField()
    file_name = serializers.CharField()
    file_size = serializers.IntegerField()
    file_type = serializers.CharField()
    is_image = serializers.BooleanField()
    file_url = serializers.URLField()
    created_at = serializers.DateTimeField()
    preview_type = serializers.CharField()
    can_preview = serializers.BooleanField()
    thumbnail_url = serializers.URLField(required=False)
    download_url = serializers.URLField(required=False)