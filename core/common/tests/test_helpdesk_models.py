"""
Tests for helpdesk models.
"""

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import AccountUser
from core.common.models import Cluster
from core.common.models.helpdesk import (
    IssueTicket,
    IssueComment,
    IssueAttachment,
    IssueStatusHistory,
    IssueType,
    IssueStatus,
    IssuePriority,
)


class IssueTicketModelTest(TestCase):
    """Test cases for IssueTicket model"""
    
    def setUp(self):
        """Set up test data"""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.user = AccountUser.objects.create_user(
            email_address="test@example.com",
            name="Test User",
            phone_number="+1234567890",
            password="testpass123"
        )
        self.user.clusters.add(self.cluster)
        
        self.staff_user = AccountUser.objects.create_user(
            email_address="staff@example.com",
            name="Staff User",
            phone_number="+1234567891",
            password="testpass123",
            is_cluster_staff=True
        )
        self.staff_user.clusters.add(self.cluster)
    
    def test_issue_creation(self):
        """Test creating an issue ticket"""
        issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            issue_type=IssueType.PLUMBING,
            priority=IssuePriority.HIGH,
            reported_by=self.user
        )
        
        self.assertEqual(issue.title, "Test Issue")
        self.assertEqual(issue.status, IssueStatus.SUBMITTED)
        self.assertEqual(issue.issue_type, IssueType.PLUMBING)
        self.assertEqual(issue.priority, IssuePriority.HIGH)
        self.assertEqual(issue.reported_by, self.user)
        self.assertIsNotNone(issue.issue_no)
        self.assertTrue(issue.issue_no.startswith("ISS-"))
    
    def test_issue_string_representation(self):
        """Test string representation of issue"""
        issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
        
        expected_str = f"{issue.issue_no} - Test Issue"
        self.assertEqual(str(issue), expected_str)
    
    def test_issue_status_change_tracking(self):
        """Test that status changes are tracked"""
        issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
        
        # Change status to resolved
        issue.status = IssueStatus.RESOLVED
        issue.save()
        
        issue.refresh_from_db()
        self.assertIsNotNone(issue.resolved_at)
        
        # Change status to closed
        issue.status = IssueStatus.CLOSED
        issue.save()
        
        issue.refresh_from_db()
        self.assertIsNotNone(issue.closed_at)
    
    def test_comments_count_property(self):
        """Test comments count property"""
        issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
        
        self.assertEqual(issue.comments_count, 0)
        
        # Add a comment
        IssueComment.objects.create(
            cluster=self.cluster,
            issue=issue,
            author=self.user,
            content="Test comment"
        )
        
        self.assertEqual(issue.comments_count, 1)


class IssueCommentModelTest(TestCase):
    """Test cases for IssueComment model"""
    
    def setUp(self):
        """Set up test data"""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.user = AccountUser.objects.create_user(
            email_address="test@example.com",
            name="Test User",
            phone_number="+1234567890",
            password="testpass123"
        )
        self.user.clusters.add(self.cluster)
        
        self.issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
    
    def test_comment_creation(self):
        """Test creating a comment"""
        comment = IssueComment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            author=self.user,
            content="This is a test comment"
        )
        
        self.assertEqual(comment.content, "This is a test comment")
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.issue, self.issue)
        self.assertFalse(comment.is_internal)
    
    def test_comment_string_representation(self):
        """Test string representation of comment"""
        comment = IssueComment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            author=self.user,
            content="This is a test comment"
        )
        
        expected_str = f"Comment on {self.issue.issue_no} by {self.user.name}"
        self.assertEqual(str(comment), expected_str)
    
    def test_threaded_comments(self):
        """Test threaded comment functionality"""
        parent_comment = IssueComment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            author=self.user,
            content="Parent comment"
        )
        
        reply_comment = IssueComment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            author=self.user,
            content="Reply comment",
            parent=parent_comment
        )
        
        self.assertEqual(reply_comment.parent, parent_comment)
        self.assertIn(reply_comment, parent_comment.replies.all())


class IssueAttachmentModelTest(TestCase):
    """Test cases for IssueAttachment model"""
    
    def setUp(self):
        """Set up test data"""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.user = AccountUser.objects.create_user(
            email_address="test@example.com",
            name="Test User",
            phone_number="+1234567890",
            password="testpass123"
        )
        self.user.clusters.add(self.cluster)
        
        self.issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
    
    def test_issue_attachment_creation(self):
        """Test creating an attachment for an issue"""
        attachment = IssueAttachment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            file_name="test.jpg",
            file_url="https://example.com/test.jpg",
            file_size=1024,
            file_type="image/jpeg",
            uploaded_by=self.user
        )
        
        self.assertEqual(attachment.file_name, "test.jpg")
        self.assertEqual(attachment.issue, self.issue)
        self.assertEqual(attachment.uploaded_by, self.user)
    
    def test_comment_attachment_creation(self):
        """Test creating an attachment for a comment"""
        comment = IssueComment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            author=self.user,
            content="Comment with attachment"
        )
        
        attachment = IssueAttachment.objects.create(
            cluster=self.cluster,
            comment=comment,
            file_name="test.pdf",
            file_url="https://example.com/test.pdf",
            file_size=2048,
            file_type="application/pdf",
            uploaded_by=self.user
        )
        
        self.assertEqual(attachment.comment, comment)
        self.assertIsNone(attachment.issue)
    
    def test_attachment_string_representation(self):
        """Test string representation of attachment"""
        attachment = IssueAttachment.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            file_name="test.jpg",
            file_url="https://example.com/test.jpg",
            file_size=1024,
            file_type="image/jpeg",
            uploaded_by=self.user
        )
        
        expected_str = f"Attachment for {self.issue.issue_no}: test.jpg"
        self.assertEqual(str(attachment), expected_str)


class IssueStatusHistoryModelTest(TestCase):
    """Test cases for IssueStatusHistory model"""
    
    def setUp(self):
        """Set up test data"""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.user = AccountUser.objects.create_user(
            email_address="test@example.com",
            name="Test User",
            phone_number="+1234567890",
            password="testpass123"
        )
        self.user.clusters.add(self.cluster)
        
        self.issue = IssueTicket.objects.create(
            cluster=self.cluster,
            title="Test Issue",
            description="This is a test issue",
            reported_by=self.user
        )
    
    def test_status_history_creation(self):
        """Test creating status history"""
        history = IssueStatusHistory.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            from_status=IssueStatus.SUBMITTED,
            to_status=IssueStatus.IN_PROGRESS,
            changed_by=self.user,
            notes="Started working on the issue"
        )
        
        self.assertEqual(history.from_status, IssueStatus.SUBMITTED)
        self.assertEqual(history.to_status, IssueStatus.IN_PROGRESS)
        self.assertEqual(history.changed_by, self.user)
        self.assertEqual(history.notes, "Started working on the issue")
    
    def test_status_history_string_representation(self):
        """Test string representation of status history"""
        history = IssueStatusHistory.objects.create(
            cluster=self.cluster,
            issue=self.issue,
            from_status=IssueStatus.SUBMITTED,
            to_status=IssueStatus.IN_PROGRESS,
            changed_by=self.user
        )
        
        expected_str = f"{self.issue.issue_no}: {IssueStatus.SUBMITTED} → {IssueStatus.IN_PROGRESS}"
        self.assertEqual(str(history), expected_str)