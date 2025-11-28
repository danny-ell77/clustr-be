"""
Chat views for ClustR members app.
Allows estate residents to participate in chat conversations,
send messages, and manage their chat settings.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count

from core.common.models import Chat, Message, ChatParticipant
from core.common.serializers.chat import (
    ChatSerializer,
    ChatListSerializer,
    ChatCreateSerializer,
    MessageSerializer,
    MessageListSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    ChatParticipantSerializer,
)
from core.common.permissions import CommunicationsPermissions
from accounts.permissions import PermissionRequiredMixin


class ChatViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    ViewSet for chat conversations for estate residents.
    Allows residents to view, create, and participate in chats.
    """

    permission_required = [CommunicationsPermissions.ViewChat]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["chat_type", "status", "is_public"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "last_message_at"]
    ordering = ["-last_message_at"]

    def get_queryset(self):
        """Get chats that the user can access"""
        user = self.request.user

        # Get chats where user is a participant or public chats
        return (
            Chat.objects.filter(
                Q(participants__user=user, participants__is_active=True)
                | Q(is_public=True),
                status="active",
            )
            .select_related("cluster")
            .prefetch_related("participants__user")
            .annotate(
                participant_count=Count(
                    "participants", filter=Q(participants__is_active=True)
                )
            )
            .distinct()
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "list":
            return ChatListSerializer
        elif self.action == "create":
            return ChatCreateSerializer
        return ChatSerializer

    def perform_create(self, serializer):
        """Ensure user has permission to create chats"""
        if not self.request.user.has_perm(CommunicationsPermissions.ManageChat):
            # For residents, only allow direct message creation
            serializer.validated_data["chat_type"] = "direct"
            serializer.validated_data["is_public"] = False

        serializer.save()

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages for a specific chat"""
        chat = self.get_object()

        # Check if user has access to this chat
        if not chat.is_public:
            try:
                chat.participants.get(user=request.user, is_active=True)
            except ChatParticipant.DoesNotExist:
                return Response(
                    {"error": "You do not have access to this chat"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        messages = (
            Message.objects.filter(
                chat=chat,
                is_deleted=False,
                status__in=["sent", "delivered", "read", "approved"],
            )
            .select_related("sender", "reply_to__sender")
            .prefetch_related("attachments")
        )

        # Mark messages as read for the current user
        if hasattr(request.user, "chat_participations"):
            try:
                participant = chat.participants.get(user=request.user, is_active=True)
                participant.mark_as_read()
            except ChatParticipant.DoesNotExist:
                pass

        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageListSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """Send a message to a specific chat"""
        chat = self.get_object()

        # Check if user can send messages to this chat
        if not chat.is_public:
            try:
                participant = chat.participants.get(user=request.user, is_active=True)
                if not participant.can_send_messages:
                    return Response(
                        {
                            "error": "You do not have permission to send messages in this chat"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except ChatParticipant.DoesNotExist:
                return Response(
                    {"error": "You are not a participant in this chat"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = MessageCreateSerializer(
            data=request.data, context={"request": request, "chat_id": chat.id}
        )
        if serializer.is_valid():
            message = serializer.save()

            # If chat is moderated, set message status to pending
            if chat.is_moderated:
                message.status = "moderated"
                message.save(update_fields=["status"])

            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Join a public chat"""
        chat = self.get_object()

        if not chat.can_user_join(request.user):
            return Response(
                {"error": "You cannot join this chat"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participant, created = ChatParticipant.objects.get_or_create(
            chat=chat,
            user=request.user,
            defaults={"cluster": chat.cluster, "is_active": True},
        )

        if not created and not participant.is_active:
            participant.rejoin_chat()

        serializer = ChatParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        """Leave a chat"""
        chat = self.get_object()

        try:
            participant = chat.participants.get(user=request.user, is_active=True)
            participant.leave_chat()
            return Response({"message": "Left chat successfully"})
        except ChatParticipant.DoesNotExist:
            return Response(
                {"error": "You are not a participant in this chat"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["patch"])
    def mute(self, request, pk=None):
        """Mute notifications for a chat"""
        chat = self.get_object()
        duration_hours = request.data.get("duration_hours", 24)

        try:
            participant = chat.participants.get(user=request.user, is_active=True)
            participant.mute_notifications(duration_hours)
            serializer = ChatParticipantSerializer(participant)
            return Response(serializer.data)
        except ChatParticipant.DoesNotExist:
            return Response(
                {"error": "You are not a participant in this chat"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["patch"])
    def unmute(self, request, pk=None):
        """Unmute notifications for a chat"""
        chat = self.get_object()

        try:
            participant = chat.participants.get(user=request.user, is_active=True)
            participant.unmute_notifications()
            serializer = ChatParticipantSerializer(participant)
            return Response(serializer.data)
        except ChatParticipant.DoesNotExist:
            return Response(
                {"error": "You are not a participant in this chat"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MessageViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing individual messages.
    Allows users to edit, delete, and react to messages.
    """

    permission_required = [CommunicationsPermissions.ViewChat]
    serializer_class = MessageSerializer

    def get_queryset(self):
        """Get messages that the user can access"""
        user = self.request.user

        return (
            Message.objects.filter(
                Q(chat__participants__user=user, chat__participants__is_active=True)
                | Q(chat__is_public=True),
                is_deleted=False,
                status__in=["sent", "delivered", "read", "approved"],
            )
            .select_related("sender", "chat", "reply_to")
            .prefetch_related("attachments")
        )

    def update(self, request, *args, **kwargs):
        """Update a message (edit content)"""
        message = self.get_object()

        # Check if user can edit this message
        if message.sender != request.user:
            return Response(
                {"error": "You can only edit your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not message.can_be_edited:
            return Response(
                {"error": "This message can no longer be edited"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MessageUpdateSerializer(message, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a message"""
        message = self.get_object()

        # Check if user can delete this message
        if message.sender != request.user:
            return Response(
                {"error": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        message.soft_delete("Deleted by user")
        return Response({"message": "Message deleted successfully"})

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        """Reply to a message"""
        parent_message = self.get_object()

        # Check if user has access to the chat
        chat = parent_message.chat
        if not chat.is_public:
            try:
                participant = chat.participants.get(user=request.user, is_active=True)
                if not participant.can_send_messages:
                    return Response(
                        {
                            "error": "You do not have permission to send messages in this chat"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except ChatParticipant.DoesNotExist:
                return Response(
                    {"error": "You are not a participant in this chat"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Set reply_to field
        data = request.data.copy()
        data["reply_to"] = parent_message.id

        serializer = MessageCreateSerializer(
            data=data, context={"request": request, "chat_id": chat.id}
        )
        if serializer.is_valid():
            message = serializer.save()

            # If chat is moderated, set message status to pending
            if chat.is_moderated:
                message.status = "moderated"
                message.save(update_fields=["status"])

            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
