"""
Serializers for chat functionality.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.common.models import Chat, ChatParticipant, Message, ChatType, MessageType
from accounts.serializers.users import UserSummarySerializer

User = get_user_model()


class ChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for chat participants"""
    
    user = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = ChatParticipant
        fields = [
            'id', 'user', 'joined_at', 'last_read_at', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    
    sender = UserSummarySerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    attachment_name = serializers.CharField(read_only=True)
    attachment_size = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'message_type', 'sender', 'created_at',
            'is_edited', 'edited_at', 'reply_to', 'attachment',
            'attachment_name', 'attachment_size', 'status'
        ]
        read_only_fields = [
            'id', 'sender', 'created_at', 'is_edited', 'edited_at',
            'attachment_name', 'attachment_size', 'status'
        ]

    def get_reply_to(self, obj):
        """Get reply-to message information"""
        if obj.reply_to:
            return {
                'id': str(obj.reply_to.id),
                'content': obj.reply_to.content[:100] + "..." if len(obj.reply_to.content) > 100 else obj.reply_to.content,
                'sender_name': obj.reply_to.sender.get_full_name(),
                'created_at': obj.reply_to.created_at.isoformat()
            }
        return None


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat messages"""
    
    reply_to_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'reply_to_id', 'attachment']
        
    def validate_content(self, value):
        """Validate message content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        
        if len(value) > 5000:  # Reasonable message length limit
            raise serializers.ValidationError("Message content is too long")
            
        return value.strip()

    def validate_reply_to_id(self, value):
        """Validate reply-to message exists in the same chat"""
        if value:
            chat_id = self.context.get('chat_id')
            if not chat_id:
                raise serializers.ValidationError("Chat context is required")
                
            try:
                Message.objects.get(id=value, chat_id=chat_id)
            except Message.DoesNotExist:
                raise serializers.ValidationError("Reply-to message not found in this chat")
                
        return value


class ChatSerializer(serializers.ModelSerializer):
    """Serializer for chat conversations"""
    
    participants = ChatParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'chat_type', 'name', 'is_active', 'created_at',
            'last_message_at', 'participants', 'last_message',
            'unread_count', 'other_participant'
        ]
        read_only_fields = ['id', 'created_at', 'last_message_at']

    def get_last_message(self, obj):
        """Get the last message in the chat"""
        last_message = obj.messages.select_related('sender').first()
        if last_message:
            return {
                'id': str(last_message.id),
                'content': last_message.content,
                'sender_name': last_message.sender.get_full_name(),
                'created_at': last_message.created_at.isoformat(),
                'message_type': last_message.message_type
            }
        return None

    def get_unread_count(self, obj):
        """Get unread message count for the current user"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.get_unread_count_for_user(user)
        return 0

    def get_other_participant(self, obj):
        """Get the other participant in individual chats"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user and obj.chat_type == ChatType.INDIVIDUAL:
            other_participant = obj.get_other_participant(user)
            if other_participant:
                return {
                    'id': str(other_participant.user.id),
                    'name': other_participant.user.get_full_name(),
                    'email': other_participant.user.email
                }
        return None


class ChatCreateSerializer(serializers.Serializer):
    """Serializer for creating individual chats"""
    
    participant_id = serializers.UUIDField()
    
    def validate_participant_id(self, value):
        """Validate that the participant exists and is not the current user"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
            
        if str(value) == str(request.user.id):
            raise serializers.ValidationError("Cannot create chat with yourself")
            
        try:
            User.objects.get(id=value, cluster=request.user.cluster)
        except User.DoesNotExist:
            raise serializers.ValidationError("Participant not found")
            
        return value


class ChatSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for chat summaries"""
    
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'chat_type', 'name', 'last_message_at',
            'last_message', 'unread_count', 'other_participant_name'
        ]

    def get_last_message(self, obj):
        """Get last message preview"""
        last_message = obj.messages.select_related('sender').first()
        if last_message:
            return {
                'content': last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
                'sender_name': last_message.sender.get_full_name(),
                'created_at': last_message.created_at.isoformat()
            }
        return None

    def get_unread_count(self, obj):
        """Get unread count for current user"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.get_unread_count_for_user(user)
        return 0

    def get_other_participant_name(self, obj):
        """Get other participant name for individual chats"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user and obj.chat_type == ChatType.INDIVIDUAL:
            other_participant = obj.get_other_participant(user)
            if other_participant:
                return other_participant.user.get_full_name()
        return obj.name