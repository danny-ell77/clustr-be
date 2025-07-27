"""
Payment management URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from management.views_payment import PaymentManagementViewSet

router = DefaultRouter()
router.register(r'payments', PaymentManagementViewSet, basename='payment-management')

urlpatterns = [
    path('', include(router.urls)),
]