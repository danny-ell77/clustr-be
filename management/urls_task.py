"""
Task management URL configuration for ClustR management app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views_task

app_name = "management_task"

# Create a router for task ViewSets
router = DefaultRouter()
router.register(r'tasks', views_task.ManagementTaskViewSet, basename='management-task')
router.register(r'task-comments', views_task.ManagementTaskCommentViewSet, basename='management-task-comment')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]