"""
Chat serializers for ClustR chat system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.common.models import Chat, ChatParticipant
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
            "last_read_at",
            "notification_settings",
            "muted_until",
            "unread_count",
            "display_name",
        ]
        read_only_fields = ["id", "joined_at", "unread_count", "display_name"]

    def get_unread_count(self, obj):
        return obj.get_unread_count()


class ChatListSerializer(serializers.ModelSerializer):
    """Serializer for chat list view"""

    participant_count = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "name",
            "description",
            "chat_type",
            "status",
            "is_public",
            "avatar",
            "last_message_at",
            "participant_count",
            "last_message",
            "unread_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        last_message = obj.get_last_message()
        if last_message:
            from .message import MessageListSerializer

            return MessageListSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                participant = obj.participants.get(user=request.user, is_active=True)
                return participant.get_unread_count()
            except ChatParticipant.DoesNotExist:
                pass
        return 0


class ChatSerializer(serializers.ModelSerializer):
    """Detailed chat serializer"""

    participants = ChatParticipantSerializer(many=True, read_only=True)
    participant_count = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()
    can_user_join = serializers.SerializerMethodField()
    user_participation = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "name",
            "description",
            "chat_type",
            "status",
            "is_public",
            "is_moderated",
            "max_participants",
            "avatar",
            "last_message_at",
            "message_count",
            "participants",
            "participant_count",
            "last_message",
            "can_user_join",
            "user_participation",
            "created_at",
            "last_modified_at",
        ]
        read_only_fields = [
            "id",
            "last_message_at",
            "message_count",
            "participant_count",
            "last_message",
            "can_user_join",
            "user_participation",
            "created_at",
            "last_modified_at",
        ]

    def get_last_message(self, obj):
        last_message = obj.get_last_message()
        if last_message:
            from .message import MessageListSerializer

            return MessageListSerializer(last_message).data
        return None

    def get_can_user_join(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.can_user_join(request.user)
        return False

    def get_user_participation(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                participant = obj.participants.get(user=request.user, is_active=True)
                return ChatParticipantSerializer(participant).data
            except ChatParticipant.DoesNotExist:
                pass
        return None


class ChatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chats"""

    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to add as participants",
    )

    class Meta:
        model = Chat
        fields = [
            "name",
            "description",
            "chat_type",
            "is_public",
            "is_moderated",
            "max_participants",
            "avatar",
            "participant_ids",
        ]

    def validate_participant_ids(self, value):
        """Validate that all participant IDs exist"""
        if value:
            existing_users = User.objects.filter(id__in=value).values_list(
                "id", flat=True
            )
            missing_users = set(value) - set(existing_users)
            if missing_users:
                raise serializers.ValidationError(
                    f"Users with IDs {list(missing_users)} do not exist"
                )
        return value

    def create(self, validated_data):
        participant_ids = validated_data.pop("participant_ids", [])
        request = self.context.get("request")

        # Set cluster from request context
        if request and hasattr(request, "cluster_context"):
            validated_data["cluster"] = request.cluster_context

        chat = super().create(validated_data)

        # Add creator as admin participant
        if request and request.user.is_authenticated:
            ChatParticipant.objects.create(
                chat=chat, user=request.user, is_admin=True, cluster=chat.cluster
            )

        # Add other participants
        if participant_ids:
            participants_to_create = []
            for user_id in participant_ids:
                if request and str(request.user.id) != str(
                    user_id
                ):  # Don't duplicate creator
                    participants_to_create.append(
                        ChatParticipant(
                            chat=chat, user_id=user_id, cluster=chat.cluster
                        )
                    )

            if participants_to_create:
                ChatParticipant.objects.bulk_create(participants_to_create)

        return chat
