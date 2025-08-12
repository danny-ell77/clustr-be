from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_password
from . import views_profile
from . import views_visitor
from . import views_invitation
from . import views_announcement
from . import views_child
from . import views_maintenance

app_name = "members"

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'maintenance-requests', views_maintenance.MemberMaintenanceLogViewSet, basename='member-maintenance-request')
router.register(r'visitors', views_visitor.MemberVisitorViewSet, basename='member-visitor')
router.register(r'visitor-logs', views_visitor.MemberVisitorLogViewSet, basename='member-visitor-log')
router.register(r'children', views_child.MemberChildViewSet, basename='member-child')
router.register(r'exit-requests', views_child.MemberExitRequestViewSet, basename='member-exit-request')
router.register(r'entry-exit-logs', views_child.MemberEntryExitLogViewSet, basename='member-entry-exit-log')
router.register(r'invitations', views_invitation.MemberInvitationViewSet, basename='member-invitation')

urlpatterns = [
    # Authentication endpoints
    path('register/', views.MemberRegistrationView.as_view(), name='register'),
    path('login/', views.MemberLoginView.as_view(), name='login'),
    
    # Password management endpoints
    path('change-password/', views_password.ChangePasswordView.as_view(), name='change_password'),
    path('reset-password/request/', views_password.RequestPasswordResetView.as_view(), name='request_password_reset'),
    path('reset-password/reset/', views_password.ResetPasswordView.as_view(), name='reset_password'),
    
    # Phone verification endpoints
    path('verify-phone/request/', views.RequestPhoneVerificationView.as_view(), name='request_phone_verification'),
    path('verify-phone/verify/', views.VerifyPhoneView.as_view(), name='verify_phone'),
    
    # Profile management endpoints
    path('profile/', views.MemberProfileView.as_view(), name='profile'),
    path('profile/upload-picture/', views_profile.ProfilePictureUploadView.as_view(), name='upload_profile_picture'),
    path('profile/verify-update/request/', views_profile.RequestProfileUpdateVerificationView.as_view(), name='request_profile_update_verification'),
    path('profile/verify-update/verify/', views_profile.VerifyProfileUpdateView.as_view(), name='verify_profile_update'),
    
    # Emergency contact endpoints
    path('emergency-contacts/', views.EmergencyContactListView.as_view(), name='emergency_contacts'),
    path('emergency-contacts/<uuid:pk>/', views.EmergencyContactDetailView.as_view(), name='emergency_contact_detail'),
    
    # Include router URLs
    path('', include(router.urls)),
    
    # Maintenance specific function-based views that are not part of viewsets
    path('maintenance/choices/', views_maintenance.maintenance_choices, name='maintenance-choices'),
    
    # Include helpdesk URLs
    path('', include('members.urls_helpdesk')),
    
    # Include emergency URLs
    path('', include('members.urls_emergency')),
    
    # Include payment URLs
    path('', include('members.urls_payment')),
    
    # Include chat URLs
    # path('', include('members.urls_chat')),
]
