"""
Message serializers for ClustR chat system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.common.models import Message, MessageAttachment
from accounts.models import AccountUser

User = get_user_model()


class MessageSenderSerializer(serializers.ModelSerializer):
    """Serializer for message sender info"""

    class Meta:
        model = AccountUser
        fields = ["id", "email", "first_name", "last_name", "profile_picture"]
        read_only_fields = fields


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments"""

    file_size_human = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()
    is_audio = serializers.ReadOnlyField()

    class Meta:
        model = MessageAttachment
        fields = [
            "id",
            "file",
            "original_filename",
            "file_size",
            "file_size_human",
            "mime_type",
            "thumbnail",
            "is_image",
            "is_video",
            "is_audio",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "file_size",
            "file_size_human",
            "mime_type",
            "is_image",
            "is_video",
            "is_audio",
            "created_at",
        ]


class ReplyToMessageSerializer(serializers.ModelSerializer):
    """Serializer for reply-to message preview"""

    sender = MessageSenderSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "content", "message_type", "sender", "created_at"]
        read_only_fields = fields


class MessageListSerializer(serializers.ModelSerializer):
    """Serializer for message list view"""

    sender = MessageSenderSerializer(read_only=True)
    reply_to = ReplyToMessageSerializer(read_only=True)
    reply_count = serializers.ReadOnlyField()
    can_be_edited = serializers.ReadOnlyField()

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "message_type",
            "status",
            "sender",
            "reply_to",
            "is_edited",
            "edited_at",
            "is_pinned",
            "is_deleted",
            "metadata",
            "reply_count",
            "can_be_edited",
            "created_at",
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Detailed message serializer"""

    sender = MessageSenderSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reply_to = ReplyToMessageSerializer(read_only=True)
    replies = MessageListSerializer(many=True, read_only=True)
    reply_count = serializers.ReadOnlyField()
    can_be_edited = serializers.ReadOnlyField()

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "message_type",
            "status",
            "sender",
            "reply_to",
            "attachments",
            "replies",
            "is_edited",
            "edited_at",
            "is_pinned",
            "is_deleted",
            "deleted_at",
            "metadata",
            "moderation_reason",
            "reply_count",
            "can_be_edited",
            "created_at",
            "last_modified_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "attachments",
            "replies",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "reply_count",
            "can_be_edited",
            "created_at",
            "last_modified_at",
        ]


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""

    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of files to attach to the message",
    )

    class Meta:
        model = Message
        fields = ["content", "message_type", "reply_to", "metadata", "attachments"]

    def validate_content(self, value):
        """Validate message content"""
        if not value and self.initial_data.get("message_type") == "text":
            raise serializers.ValidationError("Text messages cannot be empty")
        return value

    def validate_reply_to(self, value):
        """Validate reply-to message exists in the same chat"""
        if value:
            chat_id = self.context.get("chat_id")
            if chat_id and str(value.chat.id) != str(chat_id):
                raise serializers.ValidationError(
                    "Reply-to message must be from the same chat"
                )
        return value

    def create(self, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        request = self.context.get("request")
        chat_id = self.context.get("chat_id")

        # Set required fields
        validated_data["sender"] = request.user
        validated_data["chat_id"] = chat_id
        validated_data["cluster"] = request.cluster_context

        message = super().create(validated_data)

        # Create attachments
        if attachments_data:
            attachments_to_create = []
            for attachment_file in attachments_data:
                attachments_to_create.append(
                    MessageAttachment(
                        message=message, file=attachment_file, cluster=message.cluster
                    )
                )

            if attachments_to_create:
                MessageAttachment.objects.bulk_create(attachments_to_create)

        return message


class MessageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating messages"""

    class Meta:
        model = Message
        fields = ["content"]

    def validate_content(self, value):
        """Validate message content"""
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value

    def update(self, instance, validated_data):
        """Update message content with edit tracking"""
        new_content = validated_data.get("content")
        if new_content and new_content != instance.content:
            instance.edit_content(new_content)
        return instance
