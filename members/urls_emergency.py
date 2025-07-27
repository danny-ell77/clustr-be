"""
Emergency management URLs for members app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from members.views_emergency import (
    EmergencyContactViewSet,
    SOSAlertViewSet,
    EmergencyResponseViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'emergency-contacts', EmergencyContactViewSet, basename='emergency-contacts')
router.register(r'sos-alerts', SOSAlertViewSet, basename='sos-alerts')
router.register(r'emergency-responses', EmergencyResponseViewSet, basename='emergency-responses')

urlpatterns = [
    path('', include(router.urls)),
]