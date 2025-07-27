"""
Serializers for announcement-related models.
"""

from rest_framework import serializers
from django.utils import timezone

from core.common.models import (
    Announcement,
    AnnouncementView,
    AnnouncementLike,
    AnnouncementComment,
    AnnouncementAttachment,
    AnnouncementReadStatus,
    AnnouncementCategory,
)


class AnnouncementAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for announcement attachments.
    """
    preview_type = serializers.SerializerMethodField()
    can_preview = serializers.SerializerMethodField()
    file_size_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = AnnouncementAttachment
        fields = [
            'id',
            'file_name',
            'file_url',
            'file_size',
            'file_size_formatted',
            'file_type',
            'is_image',
            'preview_type',
            'can_preview',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_preview_type(self, obj):
        """Get the preview type for the attachment."""
        from core.common.utils.file_storage import FileStorage
        
        if obj.is_image:
            return 'image'
        elif FileStorage.is_valid_document(obj.file_name):
            return 'document'
        else:
            return 'file'
    
    def get_can_preview(self, obj):
        """Check if the attachment can be previewed."""
        if obj.is_image:
            return True
        elif obj.file_type == 'application/pdf':
            return True
        else:
            return False
    
    def get_file_size_formatted(self, obj):
        """Get formatted file size."""
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


class AnnouncementCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for announcement comments.
    """
    author_name = serializers.CharField(source='author.name', read_only=True)
    
    class Meta:
        model = AnnouncementComment
        fields = [
            'id',
            'content',
            'author_id',
            'author_name',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = ['id', 'author_id', 'author_name', 'created_at', 'last_modified_at']


class AnnouncementCommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating announcement comments.
    """
    class Meta:
        model = AnnouncementComment
        fields = ['content']
        
    def validate_content(self, value):
        """
        Validate comment content.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Comment content cannot be empty.")
        return value.strip()


class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer for announcements.
    """
    author_name = serializers.CharField(source='author.name', read_only=True)
    attachments = AnnouncementAttachmentSerializer(many=True, read_only=True)
    comments = AnnouncementCommentSerializer(many=True, read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    is_read_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id',
            'title',
            'content',
            'category',
            'author_id',
            'author_name',
            'views_count',
            'likes_count',
            'comments_count',
            'published_at',
            'expires_at',
            'is_published',
            'attachments',
            'comments',
            'is_liked_by_user',
            'is_read_by_user',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = [
            'id',
            'author_id',
            'author_name',
            'views_count',
            'likes_count',
            'comments_count',
            'attachments',
            'comments',
            'is_liked_by_user',
            'is_read_by_user',
            'created_at',
            'last_modified_at',
        ]
    
    def get_is_liked_by_user(self, obj):
        """
        Check if the current user has liked this announcement.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return AnnouncementLike.objects.filter(
                announcement=obj,
                user_id=request.user.id
            ).exists()
        return False
    
    def get_is_read_by_user(self, obj):
        """
        Check if the current user has read this announcement.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            read_status = AnnouncementReadStatus.objects.filter(
                announcement=obj,
                user_id=request.user.id
            ).first()
            return read_status.is_read if read_status else False
        return False


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating announcements.
    """
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of pre-uploaded attachment IDs to link to the announcement"
    )
    
    class Meta:
        model = Announcement
        fields = [
            'title',
            'content',
            'category',
            'published_at',
            'expires_at',
            'is_published',
            'attachment_ids',
        ]
        
    def validate_title(self, value):
        """
        Validate announcement title.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()
    
    def validate_content(self, value):
        """
        Validate announcement content.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value.strip()
    
    def validate_category(self, value):
        """
        Validate announcement category.
        """
        if value not in [choice[0] for choice in AnnouncementCategory.choices]:
            raise serializers.ValidationError("Invalid category.")
        return value
    
    def validate(self, attrs):
        """
        Validate the entire announcement data.
        """
        published_at = attrs.get('published_at')
        expires_at = attrs.get('expires_at')
        
        # If published_at is not provided and is_published is True, set to now
        if attrs.get('is_published', True) and not published_at:
            attrs['published_at'] = timezone.now()
        
        # Validate expiration date
        if expires_at and published_at and expires_at <= published_at:
            raise serializers.ValidationError(
                "Expiration date must be after publication date."
            )
        
        return attrs


class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating announcements.
    """
    class Meta:
        model = Announcement
        fields = [
            'title',
            'content',
            'category',
            'published_at',
            'expires_at',
            'is_published',
        ]
        
    def validate_title(self, value):
        """
        Validate announcement title.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()
    
    def validate_content(self, value):
        """
        Validate announcement content.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value.strip()


class AnnouncementLikeSerializer(serializers.ModelSerializer):
    """
    Serializer for announcement likes.
    """
    class Meta:
        model = AnnouncementLike
        fields = [
            'id',
            'user_id',
            'liked_at',
        ]
        read_only_fields = ['id', 'user_id', 'liked_at']


class AnnouncementViewSerializer(serializers.ModelSerializer):
    """
    Serializer for announcement views.
    """
    class Meta:
        model = AnnouncementView
        fields = [
            'id',
            'user_id',
            'viewed_at',
        ]
        read_only_fields = ['id', 'user_id', 'viewed_at']


class AnnouncementReadStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for announcement read status.
    """
    class Meta:
        model = AnnouncementReadStatus
        fields = [
            'id',
            'user_id',
            'is_read',
            'read_at',
        ]
        read_only_fields = ['id', 'user_id', 'read_at']