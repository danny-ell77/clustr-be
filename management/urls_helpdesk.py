"""
URL configuration for management helpdesk views.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from management.views_helpdesk import (
    ManagementIssueTicketViewSet,
    ManagementIssueCommentViewSet,
    ManagementIssueAttachmentViewSet,
)

# Create the main router
router = DefaultRouter()
router.register(r'issues', ManagementIssueTicketViewSet, basename='management-issues')

# Create nested routers for comments and attachments
issues_router = routers.NestedDefaultRouter(router, r'issues', lookup='issue')
issues_router.register(r'comments', ManagementIssueCommentViewSet, basename='management-issue-comments')
issues_router.register(r'attachments', ManagementIssueAttachmentViewSet, basename='management-issue-attachments')

# Create nested router for comment attachments
comments_router = routers.NestedDefaultRouter(issues_router, r'comments', lookup='comment')
comments_router.register(r'attachments', ManagementIssueAttachmentViewSet, basename='management-comment-attachments')

urlpatterns = [
    path('helpdesk/', include(router.urls)),
    path('helpdesk/', include(issues_router.urls)),
    path('helpdesk/', include(comments_router.urls)),
]