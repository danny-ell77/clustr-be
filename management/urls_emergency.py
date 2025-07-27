"""
Emergency management URLs for management app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from management.views_emergency import (
    EmergencyContactManagementViewSet,
    SOSAlertManagementViewSet,
    EmergencyResponseManagementViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'emergency-contacts', EmergencyContactManagementViewSet, basename='emergency-contacts-management')
router.register(r'sos-alerts', SOSAlertManagementViewSet, basename='sos-alerts-management')
router.register(r'emergency-responses', EmergencyResponseManagementViewSet, basename='emergency-responses-management')

urlpatterns = [
    path('', include(router.urls)),
]