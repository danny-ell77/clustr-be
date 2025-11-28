"""
Chat participant serializers for ClustR chat system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.common.models import ChatParticipant
from accounts.models import AccountUser

User = get_user_model()


class ChatParticipantUserSerializer(serializers.ModelSerializer):
    """Serializer for user info in chat participants"""

    class Meta:
        model = AccountUser
        fields = ["id", "email", "first_name", "last_name", "profile_picture"]
        read_only_fields = fields


class ChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for chat participants"""

    user = ChatParticipantUserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = ChatParticipant
        fields = [
            "id",
            "user",
            "is_active",
            "is_admin",
            "is_moderator",
            "can_send_messages",
            "can_add_participants",
            "joined_at",
            "left_at",
            "last_read_at",
            "notification_settings",
            "muted_until",
            "unread_count",
            "display_name",
        ]
        read_only_fields = [
            "id",
            "user",
            "joined_at",
            "left_at",
            "last_read_at",
            "unread_count",
            "display_name",
        ]

    def get_unread_count(self, obj):
        return obj.get_unread_count()


class ChatParticipantCreateSerializer(serializers.Serializer):
    """Serializer for adding participants to a chat"""

    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of user IDs to add as participants",
    )

    def validate_user_ids(self, value):
        """Validate that all user IDs exist"""
        existing_users = User.objects.filter(id__in=value).values_list("id", flat=True)
        missing_users = set(value) - set(existing_users)
        if missing_users:
            raise serializers.ValidationError(
                f"Users with IDs {list(missing_users)} do not exist"
            )
        return value


class ChatParticipantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating chat participant settings"""

    class Meta:
        model = ChatParticipant
        fields = [
            "is_admin",
            "is_moderator",
            "can_send_messages",
            "can_add_participants",
            "notification_settings",
        ]
