from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from . import views
from . import views_visitor
from . import views_invitation
from . import views_event
from . import views_announcement
from . import views_child
from . import views_maintenance

app_name = "management"

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'visitors', views_visitor.ManagementVisitorViewSet, basename='management-visitor')
router.register(r'visitor-logs', views_visitor.ManagementVisitorLogViewSet, basename='management-visitor-log')
router.register(r'invitations', views_invitation.ManagementInvitationViewSet, basename='management-invitation')
router.register(r'events', views_event.ManagementEventViewSet, basename='management-event')
router.register(r'announcements', views_announcement.ManagementAnnouncementViewSet, basename='management-announcement')
router.register(r'children', views_child.ManagementChildViewSet, basename='management-child')

# Maintenance router with nested structure
maintenance_router = DefaultRouter()
maintenance_router.register(r'logs', views_maintenance.MaintenanceLogViewSet, basename='management-maintenance-log')
maintenance_router.register(r'schedules', views_maintenance.MaintenanceScheduleViewSet, basename='management-maintenance-schedule')

# Create nested routers for event guests
events_router = NestedDefaultRouter(router, r'events', lookup='event')
events_router.register(r'guests', views_event.ManagementEventGuestViewSet, basename='management-event-guest')

urlpatterns = [
    # User management endpoints
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # Role management endpoints
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/<uuid:pk>/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/assign/', views.AssignRoleView.as_view(), name='assign_role'),
    
    # Include router URLs
    path('', include(router.urls)),
    path('', include(events_router.urls)),
    
    # Include maintenance URLs with nested structure
    path('maintenance/', include(maintenance_router.urls)),
    path('maintenance/categories/', views_maintenance.maintenance_categories, name='maintenance-categories'),
    path('maintenance/choices/', views_maintenance.maintenance_choices, name='maintenance-choices'),
    
    # Include helpdesk URLs
    path('', include('management.urls_helpdesk')),
    
    # Include emergency URLs with emergency/ prefix
    path('emergency/', include('management.urls_emergency')),
    
    # Include shift management URLs
    path('', include('management.urls_shift')),
    
    # Include task management URLs
    path('', include('management.urls_task')),
    
    # Include payment management URLs
    path('', include('management.urls_payment')),
    
    # Include resident management URLs
    path('', include('management.urls_resident')),
    
    # Include chat URLs
    # path('', include('management.urls_chat')),
]
