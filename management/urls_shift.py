"""
URL patterns for shift management in ClustR management app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from management.views_shift import (
    ShiftViewSet,
    ShiftSwapRequestViewSet,
    StaffScheduleView,
    ShiftReportView
)
from management.views_staff import StaffViewSet

# Create router for viewsets
router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'shift-swap-requests', ShiftSwapRequestViewSet, basename='shift-swap-request')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Staff schedule endpoints
    path('staff-schedule/', StaffScheduleView.as_view(), name='staff-schedule-all'),
    path('staff-schedule/<uuid:staff_id>/', StaffScheduleView.as_view(), name='staff-schedule-detail'),
    
    # Shift reports
    path('shift-reports/', ShiftReportView.as_view(), name='shift-reports'),
]