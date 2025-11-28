"""
URL configuration for member chat endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_chat import ChatViewSet, MessageViewSet

router = DefaultRouter()
router.register(r"chats", ChatViewSet, basename="chat")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
]
