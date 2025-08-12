"""
WebSocket consumers for ClustR real-time features.
"""

import json
import logging
from typing import Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from accounts.models import AccountUser
from core.common.models import Chat, Message, ChatParticipant, MessageType

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    Handles individual chat conversations between users.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        self.user = self.scope.get('user')

        # Check if user is authenticated
        if isinstance(self.user, AnonymousUser):
            await self.close(code=4001)  # Unauthorized
            return

        # Verify user has access to this chat
        has_access = await self.verify_chat_access()
        if not has_access:
            await self.close(code=4003)  # Forbidden
            return

        # Join chat group
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user.id} connected to chat {self.chat_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave chat group
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )
        logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from chat {self.chat_id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
            else:
                await self.send_error("Unknown message type")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_chat_message(self, data: Dict[str, Any]):
        """Handle incoming chat messages"""
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')

        if not content:
            await self.send_error("Message content cannot be empty")
            return

        # Create message in database
        message = await self.create_message(content, reply_to_id)
        if not message:
            await self.send_error("Failed to create message")
            return

        # Broadcast message to chat group
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message_broadcast',
                'message': await self.serialize_message(message)
            }
        )

    async def handle_typing_indicator(self, data: Dict[str, Any]):
        """Handle typing indicators"""
        is_typing = data.get('is_typing', False)
        
        # Broadcast typing indicator to other users in the chat
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'typing_indicator_broadcast',
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )

    async def handle_mark_as_read(self, data: Dict[str, Any]):
        """Handle mark as read requests"""
        await self.mark_chat_as_read()
        
        # Notify other participants that messages have been read
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'messages_read_broadcast',
                'user_id': str(self.user.id)
            }
        )

    async def chat_message_broadcast(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def typing_indicator_broadcast(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send typing indicator to the user who is typing
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))

    async def messages_read_broadcast(self, event):
        """Send messages read notification to WebSocket"""
        # Don't send read notification to the user who marked as read
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'user_id': event['user_id']
            }))

    async def send_error(self, message: str):
        """Send error message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    @database_sync_to_async
    def verify_chat_access(self) -> bool:
        """Verify that the user has access to this chat"""
        try:
            chat = Chat.objects.get(id=self.chat_id, cluster=self.user.cluster)
            return ChatParticipant.objects.filter(
                chat=chat,
                user=self.user,
                is_active=True
            ).exists()
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, content: str, reply_to_id: str = None) -> Message:
        """Create a new message in the database"""
        try:
            chat = Chat.objects.get(id=self.chat_id, cluster=self.user.cluster)
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, chat=chat)
                except Message.DoesNotExist:
                    pass

            message = Message.objects.create(
                chat=chat,
                sender=self.user,
                content=content,
                message_type=MessageType.TEXT,
                reply_to=reply_to,
                cluster=self.user.cluster
            )
            return message
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            return None

    @database_sync_to_async
    def serialize_message(self, message: Message) -> Dict[str, Any]:
        """Serialize message for WebSocket transmission"""
        return {
            'id': str(message.id),
            'content': message.content,
            'message_type': message.message_type,
            'sender': {
                'id': str(message.sender.id),
                'name': message.sender.get_full_name(),
                'email': message.sender.email
            },
            'created_at': message.created_at.isoformat(),
            'is_edited': message.is_edited,
            'reply_to': {
                'id': str(message.reply_to.id),
                'content': message.reply_to.content[:100] + "..." if len(message.reply_to.content) > 100 else message.reply_to.content,
                'sender_name': message.reply_to.sender.get_full_name()
            } if message.reply_to else None
        }

    @database_sync_to_async
    def mark_chat_as_read(self):
        """Mark all messages in the chat as read for the current user"""
        try:
            chat = Chat.objects.get(id=self.chat_id, cluster=self.user.cluster)
            participant = ChatParticipant.objects.get(chat=chat, user=self.user)
            participant.mark_as_read()
        except (Chat.DoesNotExist, ChatParticipant.DoesNotExist):
            pass