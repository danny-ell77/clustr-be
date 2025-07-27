from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
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
router.register(r'maintenance-logs', views_maintenance.MaintenanceLogViewSet, basename='management-maintenance-log')
router.register(r'maintenance-schedules', views_maintenance.MaintenanceScheduleViewSet, basename='management-maintenance-schedule')

# Create nested routers for event guests
events_router = NestedSimpleRouter(router, r'events', lookup='event')
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
    
    # Include helpdesk URLs
    path('', include('management.urls_helpdesk')),
    
    # Include emergency URLs
    path('', include('management.urls_emergency')),
    
    # Include shift management URLs
    path('', include('management.urls_shift')),
    
    # Include task management URLs
    path('', include('management.urls_task')),
    
    # Include payment management URLs
    path('', include('management.urls_payment')),

    # Maintenance specific function-based views that are not part of viewsets
    path('maintenance/categories/', views_maintenance.maintenance_categories, name='maintenance-categories'),
    path('maintenance/choices/', views_maintenance.maintenance_choices, name='maintenance-choices'),
]
