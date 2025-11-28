"""
Chat management views for ClustR management app.
Allows estate managers to manage chat conversations, moderate messages,
and oversee communication in the estate.
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
    ChatParticipantSerializer,
    ChatParticipantCreateSerializer,
)
from core.common.permissions import CommunicationsPermissions
from accounts.permissions import PermissionRequiredMixin


class ChatManagementViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing chat conversations in the estate.
    Allows estate managers to create, view, and moderate chats.
    """

    permission_required = [
        CommunicationsPermissions.ViewChat,
        CommunicationsPermissions.ManageChat,
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["chat_type", "status", "is_public", "is_moderated"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "last_message_at", "participant_count"]
    ordering = ["-last_message_at"]

    def get_queryset(self):
        """Get chats for the current cluster"""
        return (
            Chat.objects.select_related("cluster")
            .prefetch_related("participants__user")
            .annotate(
                participant_count=Count(
                    "participants", filter=Q(participants__is_active=True)
                )
            )
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "list":
            return ChatListSerializer
        elif self.action == "create":
            return ChatCreateSerializer
        return ChatSerializer

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages for a specific chat"""
        chat = self.get_object()
        messages = (
            Message.objects.filter(chat=chat, is_deleted=False)
            .select_related("sender", "reply_to__sender")
            .prefetch_related("attachments")
        )

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
            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get", "post"])
    def participants(self, request, pk=None):
        """Get or add participants for a specific chat"""
        chat = self.get_object()

        if request.method == "GET":
            participants = chat.participants.filter(is_active=True).select_related(
                "user"
            )
            serializer = ChatParticipantSerializer(participants, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            # Check permission to add participants
            try:
                participant = chat.participants.get(user=request.user, is_active=True)
                if not (participant.can_add_participants or participant.is_admin):
                    return Response(
                        {"error": "You do not have permission to add participants"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except ChatParticipant.DoesNotExist:
                return Response(
                    {"error": "You are not a participant in this chat"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = ChatParticipantCreateSerializer(data=request.data)
            if serializer.is_valid():
                user_ids = serializer.validated_data["user_ids"]

                # Add participants
                new_participants = []
                for user_id in user_ids:
                    if not chat.participants.filter(user_id=user_id).exists():
                        new_participants.append(
                            ChatParticipant(
                                chat=chat, user_id=user_id, cluster=chat.cluster
                            )
                        )

                if new_participants:
                    ChatParticipant.objects.bulk_create(new_participants)

                # Return updated participants list
                participants = chat.participants.filter(is_active=True).select_related(
                    "user"
                )
                response_serializer = ChatParticipantSerializer(participants, many=True)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"])
    def archive(self, request, pk=None):
        """Archive a chat"""
        chat = self.get_object()
        chat.status = "archived"
        chat.save(update_fields=["status"])

        serializer = self.get_serializer(chat)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def unarchive(self, request, pk=None):
        """Unarchive a chat"""
        chat = self.get_object()
        chat.status = "active"
        chat.save(update_fields=["status"])

        serializer = self.get_serializer(chat)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Get chat analytics for the estate"""
        queryset = self.get_queryset()

        analytics = {
            "total_chats": queryset.count(),
            "active_chats": queryset.filter(status="active").count(),
            "public_chats": queryset.filter(is_public=True).count(),
            "moderated_chats": queryset.filter(is_moderated=True).count(),
            "total_messages": Message.objects.filter(
                chat__cluster=request.cluster_context, is_deleted=False
            ).count(),
            "messages_today": (
                Message.objects.filter(
                    chat__cluster=request.cluster_context,
                    is_deleted=False,
                    created_at__date=(
                        request.META.get("HTTP_DATE", "").split("T")[0]
                        if "HTTP_DATE" in request.META
                        else None
                    ),
                ).count()
                if "HTTP_DATE" in request.META
                else 0
            ),
        }

        return Response(analytics)


class MessageModerationViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    ViewSet for moderating messages in chats.
    Allows estate managers to moderate, approve, or reject messages.
    """

    permission_required = [CommunicationsPermissions.ModerateChat]
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "message_type", "chat__id"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Get messages that need moderation"""
        return (
            Message.objects.filter(
                chat__cluster=self.request.cluster_context,
                status__in=["pending", "moderated"],
            )
            .select_related("sender", "chat", "reply_to")
            .prefetch_related("attachments")
        )

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        """Approve a moderated message"""
        message = self.get_object()
        message.approve_message()

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        """Reject a moderated message"""
        message = self.get_object()
        reason = request.data.get("reason", "Message rejected by moderator")
        message.reject_message(reason)

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @action(detail=True, methods=["delete"])
    def delete_message(self, request, pk=None):
        """Soft delete a message"""
        message = self.get_object()
        reason = request.data.get("reason", "Message deleted by moderator")
        message.soft_delete(reason)

        return Response({"message": "Message deleted successfully"})

    @action(detail=True, methods=["patch"])
    def pin(self, request, pk=None):
        """Pin a message in the chat"""
        message = self.get_object()
        message.pin_message()

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def unpin(self, request, pk=None):
        """Unpin a message in the chat"""
        message = self.get_object()
        message.unpin_message()

        serializer = self.get_serializer(message)
        return Response(serializer.data)
