"""
URL patterns for user settings management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from accounts.views import UserSettingsViewSet, NotificationPreferenceViewSet

# Create router for user settings
router = DefaultRouter()
router.register(r'settings', UserSettingsViewSet, basename='user-settings')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preferences')

urlpatterns = [
    path('', include(router.urls)),
]