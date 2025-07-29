"""
Serializers for help desk models.
"""

from rest_framework import serializers
from django.utils import timezone

from core.common.models.helpdesk import (
    IssueTicket,
    IssueComment,
    IssueAttachment,
    IssueStatusHistory,
    IssueStatus,
    IssueType,
    IssuePriority,
)
from accounts.serializers.users import UserSummarySerializer
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager


class IssueAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for issue attachments"""
    
    uploaded_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = IssueAttachment
        fields = [
            'id',
            'file_name',
            'file_url',
            'file_size',
            'file_type',
            'uploaded_by',
            'created_at',
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class IssueCommentSerializer(serializers.ModelSerializer):
    """Serializer for issue comments"""
    
    author = UserSummarySerializer(read_only=True)
    attachments = IssueAttachmentSerializer(many=True, read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = IssueComment
        fields = [
            'id',
            'content',
            'author',
            'is_internal',
            'parent',
            'attachments',
            'replies',
            'created_at',
            'last_modified_at',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'last_modified_at']
    
    def get_replies(self, obj):
        """Get replies to this comment"""
        if obj.replies.exists():
            return IssueCommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []


class IssueStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for issue status history"""
    
    changed_by = UserSummarySerializer(read_only=True)
    
    class Meta:
        model = IssueStatusHistory
        fields = [
            'id',
            'from_status',
            'to_status',
            'changed_by',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'changed_by', 'created_at']


class IssueTicketListSerializer(serializers.ModelSerializer):
    """Serializer for issue ticket list view"""
    
    reported_by = UserSummarySerializer(read_only=True)
    assigned_to = UserSummarySerializer(read_only=True)
    comments_count = serializers.ReadOnlyField()
    
    class Meta:
        model = IssueTicket
        fields = [
            'id',
            'issue_no',
            'title',
            'issue_type',
            'status',
            'priority',
            'reported_by',
            'assigned_to',
            'comments_count',
            'created_at',
            'last_modified_at',
            'due_date',
        ]
        read_only_fields = [
            'id',
            'issue_no',
            'reported_by',
            'comments_count',
            'created_at',
            'last_modified_at',
        ]


class IssueTicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for issue ticket detail view"""
    
    reported_by = UserSummarySerializer(read_only=True)
    assigned_to = UserSummarySerializer(read_only=True)
    comments = IssueCommentSerializer(many=True, read_only=True)
    attachments = IssueAttachmentSerializer(many=True, read_only=True)
    status_history = IssueStatusHistorySerializer(many=True, read_only=True)
    comments_count = serializers.ReadOnlyField()
    
    class Meta:
        model = IssueTicket
        fields = [
            'id',
            'issue_no',
            'title',
            'description',
            'issue_type',
            'status',
            'priority',
            'reported_by',
            'assigned_to',
            'comments',
            'attachments',
            'status_history',
            'comments_count',
            'resolution_notes',
            'created_at',
            'last_modified_at',
            'resolved_at',
            'closed_at',
            'escalated_at',
            'due_date',
        ]
        read_only_fields = [
            'id',
            'issue_no',
            'reported_by',
            'comments',
            'attachments',
            'status_history',
            'comments_count',
            'created_at',
            'last_modified_at',
            'resolved_at',
            'closed_at',
            'escalated_at',
        ]


class IssueTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating issue tickets"""
    
    class Meta:
        model = IssueTicket
        fields = [
            'title',
            'description',
            'issue_type',
            'priority',
        ]
    
    def create(self, validated_data):
        """Create a new issue ticket"""
        request = self.context.get('request')
        validated_data['reported_by'] = request.user
        validated_data['cluster'] = request.cluster_context
        return super().create(validated_data)


class IssueTicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating issue tickets"""
    
    class Meta:
        model = IssueTicket
        fields = [
            'title',
            'description',
            'issue_type',
            'status',
            'priority',
            'assigned_to',
            'resolution_notes',
            'due_date',
        ]
    
    def update(self, instance, validated_data):
        """Update issue ticket and track status changes"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Update the instance
        instance = super().update(instance, validated_data)
        
        # Track status change if status was updated
        if old_status != new_status:
            request = self.context.get('request')
            IssueStatusHistory.objects.create(
                issue=instance,
                from_status=old_status,
                to_status=new_status,
                changed_by=request.user,
                cluster=request.cluster_context,
                notes=f"Status changed from {old_status} to {new_status}"
            )
            
            # Send notification about status change
            recipients = []
            if instance.reported_by:
                recipients.append(instance.reported_by)

            NotificationManager.send(
                event=NotificationEvents.ISSUE_STATUS_CHANGED,
                recipients=recipients,
                cluster=request.cluster_context,
                context={
                    "issue_number": instance.issue_no,
                    "issue_title": instance.title,
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by_name": request.user.name,
                }
            )
        
        return instance


class IssueCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating issue comments"""
    
    class Meta:
        model = IssueComment
        fields = [
            'content',
            'is_internal',
            'parent',
        ]
    
    def create(self, validated_data):
        """Create a new issue comment"""
        request = self.context.get('request')
        issue_id = self.context.get('issue_id')
        
        validated_data['author'] = request.user
        validated_data['cluster'] = request.cluster_context
        validated_data['issue_id'] = issue_id
        
        comment = super().create(validated_data)
        
        # Send notification about new comment
        recipients = []
        if comment.issue.reported_by and comment.issue.reported_by != request.user:
            recipients.append(comment.issue.reported_by)
        if comment.issue.assigned_to and comment.issue.assigned_to != request.user:
            recipients.append(comment.issue.assigned_to)

        if recipients:
            NotificationManager.send(
                event=NotificationEvents.COMMENT_REPLY,
                recipients=recipients,
                cluster=request.cluster_context,
                context={
                    "issue_number": comment.issue.issue_no,
                    "issue_title": comment.issue.title,
                    "comment_content": comment.content,
                    "commenter_name": request.user.name,
                }
            )
        
        return comment


class IssueAttachmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating issue attachments"""
    
    class Meta:
        model = IssueAttachment
        fields = [
            'file_name',
            'file_url',
            'file_size',
            'file_type',
        ]
    
    def create(self, validated_data):
        """Create a new issue attachment"""
        request = self.context.get('request')
        issue_id = self.context.get('issue_id')
        comment_id = self.context.get('comment_id')
        
        validated_data['uploaded_by'] = request.user
        validated_data['cluster'] = request.cluster_context
        
        if issue_id:
            validated_data['issue_id'] = issue_id
        if comment_id:
            validated_data['comment_id'] = comment_id
        
        return super().create(validated_data)