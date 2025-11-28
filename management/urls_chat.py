"""
URL configuration for chat management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_chat import ChatManagementViewSet, MessageModerationViewSet

router = DefaultRouter()
router.register(r"chats", ChatManagementViewSet, basename="chat-management")
router.register(
    r"message-moderation", MessageModerationViewSet, basename="message-moderation"
)

urlpatterns = [
    path("", include(router.urls)),
]
