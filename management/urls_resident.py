"""
URL configuration for resident management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from management.views_resident import ResidentViewSet

router = DefaultRouter()
router.register(r'residents', ResidentViewSet, basename='resident')

urlpatterns = [
    path('', include(router.urls)),
]
