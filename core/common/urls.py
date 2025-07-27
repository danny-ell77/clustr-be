"""
URL patterns for core.common app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.common.views import FileUploadViewSet

# Create a router for viewsets
router = DefaultRouter()
router.register(r'files', FileUploadViewSet, basename='files')

urlpatterns = [
    path('', include(router.urls)),
]