"""
Payment URL configuration for members.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from members.views_payment import WalletViewSet, BillViewSet, RecurringPaymentViewSet

router = DefaultRouter()
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'bills', BillViewSet, basename='bills')
router.register(r'recurring-payments', RecurringPaymentViewSet, basename='recurring-payments')

urlpatterns = [
    path('', include(router.urls)),
]