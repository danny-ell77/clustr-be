"""
URL configuration for utility bill automation endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.common.views.utility_views import (
    UtilityProviderViewSet,
    UtilityBillViewSet,
    RecurringUtilityPaymentViewSet,
    UtilityPaymentViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'providers', UtilityProviderViewSet, basename='utility-providers')
router.register(r'bills', UtilityBillViewSet, basename='utility-bills')
router.register(r'recurring-payments', RecurringUtilityPaymentViewSet, basename='recurring-utility-payments')
router.register(r'payments', UtilityPaymentViewSet, basename='utility-payments')

urlpatterns = [
    path('utility/', include(router.urls)),
]