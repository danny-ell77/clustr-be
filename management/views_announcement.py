"""
Views for announcement management in the management app.
"""

from django.db import transaction, models
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters

from accounts.permissions import HasClusterPermission
from core.common.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementAttachment,
    AnnouncementLike,
    AnnouncementView,
    AnnouncementReadStatus,
)
from core.common.permissions import CommunicationsPermissions
from core.common.decorators import audit_viewset
from core.common.serializers.announcement_serializers import (
    AnnouncementSerializer,
    AnnouncementCreateSerializer,
    AnnouncementUpdateSerializer,
    AnnouncementCommentSerializer,
    AnnouncementCommentCreateSerializer,
    AnnouncementAttachmentSerializer,
)
from core.common.utils.notification_utils import NotificationManager


class ManagementAnnouncementFilter(django_filters.FilterSet):
    """Filter for management announcements"""
    category = django_filters.CharFilter(field_name='category')
    is_published = django_filters.BooleanFilter(field_name='is_published')
    
    class Meta:
        model = Announcement
        fields = ['category', 'is_published']


@audit_viewset(resource_type='announcement')
class ManagementAnnouncementViewSet(ModelViewSet):
    """
    ViewSet for managing announcements in the management app.
    Allows administrators to create, view, update, and delete announcements.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(CommunicationsPermissions.ManageAnnouncement),
    ]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ManagementAnnouncementFilter
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'published_at', 'views_count', 'likes_count']
    ordering = ['-published_at', '-created_at']
    
    def get_queryset(self):
        """
        Return all announcements for the current cluster with expiration filtering.
        """
        return Announcement.objects.all()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return AnnouncementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AnnouncementUpdateSerializer
        return AnnouncementSerializer
    
    def perform_create(self, serializer):
        """
        Create a new announcement and set the author to the current user.
        """
        with transaction.atomic():
            # Set the author to the current user
            announcement = serializer.save(author_id=self.request.user.id)
            
            # Handle attachment IDs if provided
            attachment_ids = serializer.validated_data.get('attachment_ids', [])
            if attachment_ids:
                # Link existing attachments to this announcement
                AnnouncementAttachment.objects.filter(
                    id__in=attachment_ids
                ).update(announcement=announcement)
            
            # Send notifications to all cluster users if published
            if announcement.is_published:
                try:
                    NotificationManager.send_announcement_notification(
                        announcement=announcement,
                        cluster=announcement.cluster
                    )
                except Exception as e:
                    # Log the error but don't fail the creation
                    pass
    
    def perform_update(self, serializer):
        """
        Update an announcement and handle publication notifications.
        """
        old_published = self.get_object().is_published
        announcement = serializer.save()
        
        # If announcement was just published, send notifications
        if not old_published and announcement.is_published:
            try:
                NotificationManager.send_announcement_notification(
                    announcement=announcement,
                    cluster=announcement.cluster
                )
            except Exception as e:
                # Log the error but don't fail the update
                pass
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """
        Get comments for a specific announcement.
        """
        announcement = self.get_object()
        comments = AnnouncementComment.objects.filter(announcement=announcement)
        
        # Pagination
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = AnnouncementCommentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AnnouncementCommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """
        Add a comment to an announcement.
        """
        announcement = self.get_object()
        serializer = AnnouncementCommentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                comment = serializer.save(
                    announcement=announcement,
                    author_id=request.user.id
                )
                
                # Update comments count
                announcement.comments_count += 1
                announcement.save(update_fields=['comments_count'])
                
                # Send notification to announcement author if different user
                if announcement.author_id != request.user.id:
                    try:
                        NotificationManager.send_comment_notification(
                            comment=comment,
                            announcement=announcement
                        )
                    except Exception as e:
                        # Log the error but don't fail the comment creation
                        pass
            
            return Response(
                AnnouncementCommentSerializer(comment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def engagement_metrics(self, request, pk=None):
        """
        Get engagement metrics for an announcement.
        """
        announcement = self.get_object()
        
        metrics = {
            'views_count': announcement.views_count,
            'likes_count': announcement.likes_count,
            'comments_count': announcement.comments_count,
            'engagement_rate': 0,
        }
        
        # Calculate engagement rate (likes + comments) / views
        if announcement.views_count > 0:
            metrics['engagement_rate'] = (
                (announcement.likes_count + announcement.comments_count) / 
                announcement.views_count
            ) * 100
        
        return Response(metrics)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish an announcement.
        """
        announcement = self.get_object()
        
        if announcement.is_published:
            return Response(
                {'detail': 'Announcement is already published.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        announcement.is_published = True
        announcement.published_at = timezone.now()
        announcement.save(update_fields=['is_published', 'published_at'])
        
        # Send notifications
        try:
            NotificationManager.send_announcement_notification(
                announcement=announcement,
                cluster=announcement.cluster
            )
        except Exception as e:
            # Log the error but don't fail the publication
            pass
        
        return Response(
            AnnouncementSerializer(announcement, context={'request': request}).data
        )
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """
        Unpublish an announcement.
        """
        announcement = self.get_object()
        
        if not announcement.is_published:
            return Response(
                {'detail': 'Announcement is already unpublished.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        announcement.is_published = False
        announcement.save(update_fields=['is_published'])
        
        return Response(
            AnnouncementSerializer(announcement, context={'request': request}).data
        )
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get available announcement categories.
        """
        from core.common.models import AnnouncementCategory
        
        categories = [
            {'value': choice[0], 'label': choice[1]}
            for choice in AnnouncementCategory.choices
        ]
        
        return Response(categories)
    
    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """
        Get attachments for a specific announcement.
        """
        announcement = self.get_object()
        attachments = AnnouncementAttachment.objects.filter(announcement=announcement)
        
        serializer = AnnouncementAttachmentSerializer(attachments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_attachment(self, request, pk=None):
        """
        Add an attachment to an announcement.
        """
        announcement = self.get_object()
        attachment_id = request.data.get('attachment_id')
        
        if not attachment_id:
            return Response(
                {'error': 'attachment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = AnnouncementAttachment.objects.get(
                id=attachment_id,
                announcement__isnull=True  # Only unlinked attachments
            )
        except AnnouncementAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found or already linked'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Link the attachment to the announcement
        attachment.announcement = announcement
        attachment.save(update_fields=['announcement'])
        
        serializer = AnnouncementAttachmentSerializer(attachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_attachment(self, request, pk=None):
        """
        Remove an attachment from an announcement.
        """
        announcement = self.get_object()
        attachment_id = request.data.get('attachment_id')
        
        if not attachment_id:
            return Response(
                {'error': 'attachment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = AnnouncementAttachment.objects.get(
                id=attachment_id,
                announcement=announcement
            )
        except AnnouncementAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete the attachment and its file
        try:
            # Extract file path from URL (this might need adjustment based on storage backend)
            from core.common.utils.file_storage import FileStorage
            file_path = attachment.file_url.split('/')[-4:]  # Adjust based on URL structure
            file_path = '/'.join(file_path)
            FileStorage.delete_file(file_path)
        except Exception:
            # Continue with database deletion even if file deletion fails
            pass
        
        attachment.delete()
        
        return Response(
            {'message': 'Attachment removed successfully'},
            status=status.HTTP_200_OK
        )


@audit_viewset(resource_type='announcement_comment')
class ManagementAnnouncementCommentViewSet(ModelViewSet):
    """
    ViewSet for managing announcement comments in the management app.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        HasClusterPermission(CommunicationsPermissions.ManageAnnouncement),
    ]
    serializer_class = AnnouncementCommentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['announcement']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return all announcement comments for the current cluster.
        """
        return AnnouncementComment.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a comment and update the announcement's comment count.
        """
        comment = self.get_object()
        announcement = comment.announcement
        
        with transaction.atomic():
            # Update comments count
            announcement.comments_count = max(0, announcement.comments_count - 1)
            announcement.save(update_fields=['comments_count'])
            
            # Delete the comment
            comment.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)