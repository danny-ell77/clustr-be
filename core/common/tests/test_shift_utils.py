"""
Tests for shift utilities in ClustR application.
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.common.models import Cluster, Shift, ShiftSwapRequest, ShiftAttendance, ShiftType, ShiftStatus
from core.common.includes import shifts
from accounts.models import AccountUser


class ShiftManagerTest(TestCase):
    """Test cases for ShiftManager utility."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.staff_user1 = AccountUser.objects.create_user(
            email_address="staff1@test.com",
            name="Test Staff 1",
            phone_number="+1234567890",
            is_cluster_staff=True
        )
        self.staff_user1.clusters.add(self.cluster)
        
        self.staff_user2 = AccountUser.objects.create_user(
            email_address="staff2@test.com",
            name="Test Staff 2",
            phone_number="+1234567891",
            is_cluster_staff=True
        )
        self.staff_user2.clusters.add(self.cluster)
        
        self.start_time = timezone.now() + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=8)
    
    def test_create_shift_success(self):
        """Test successful shift creation."""
        shift = shifts.create(
            cluster=self.cluster,
            title="Security Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time,
            location="Main Gate"
        )
        
        self.assertEqual(shift.title, "Security Shift")
        self.assertEqual(shift.assigned_staff, self.staff_user1)
        self.assertEqual(shift.status, ShiftStatus.SCHEDULED)
        
        # Check that attendance record was created
        self.assertTrue(hasattr(shift, 'attendance'))
        self.assertIsNotNone(shift.attendance)
    
    def test_create_shift_with_conflict(self):
        """Test shift creation with conflict detection."""
        # Create first shift
        shifts.create(
            cluster=self.cluster,
            title="First Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # Try to create overlapping shift
        with self.assertRaises(ValidationError):
            shifts.create(
                cluster=self.cluster,
                title="Overlapping Shift",
                shift_type=ShiftType.MAINTENANCE,
                assigned_staff=self.staff_user1,
                start_time=self.start_time + timedelta(hours=2),
                end_time=self.end_time + timedelta(hours=2)
            )
    
    def test_check_shift_conflicts(self):
        """Test shift conflict detection."""
        # Create a shift
        shift = shifts.create(
            cluster=self.cluster,
            title="Existing Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # Check for conflicts with overlapping time
        conflicts = shifts.check_conflicts(
            cluster=self.cluster,
            staff_member=self.staff_user1,
            start_time=self.start_time + timedelta(hours=2),
            end_time=self.end_time + timedelta(hours=2)
        )
        
        self.assertEqual(conflicts.count(), 1)
        self.assertEqual(conflicts.first(), shift)
        
        # Check for conflicts with non-overlapping time
        no_conflicts = shifts.check_conflicts(
            cluster=self.cluster,
            staff_member=self.staff_user1,
            start_time=self.end_time + timedelta(hours=1),
            end_time=self.end_time + timedelta(hours=9)
        )
        
        self.assertEqual(no_conflicts.count(), 0)
    
    def test_clock_in_staff(self):
        """Test clocking in staff."""
        shift = shifts.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        clock_in_time = timezone.now()
        updated_shift = shifts.clock_in(shift.id, clock_in_time)
        
        self.assertEqual(updated_shift.status, ShiftStatus.IN_PROGRESS)
        self.assertEqual(updated_shift.actual_start_time, clock_in_time)
        self.assertEqual(updated_shift.attendance.clock_in_time, clock_in_time)
    
    def test_clock_out_staff(self):
        """Test clocking out staff."""
        shift = shifts.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # Clock in first
        clock_in_time = timezone.now()
        shifts.clock_in(shift.id, clock_in_time)
        
        # Clock out
        clock_out_time = clock_in_time + timedelta(hours=8)
        updated_shift = shifts.clock_out(shift.id, clock_out_time)
        
        self.assertEqual(updated_shift.status, ShiftStatus.COMPLETED)
        self.assertEqual(updated_shift.actual_end_time, clock_out_time)
        self.assertEqual(updated_shift.attendance.clock_out_time, clock_out_time)
    
    def test_create_shift_swap_request(self):
        """Test creating shift swap request."""
        shift1 = shifts.create(
            cluster=self.cluster,
            title="Shift 1",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        shift2 = shifts.create(
            cluster=self.cluster,
            title="Shift 2",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user2,
            start_time=self.start_time + timedelta(days=1),
            end_time=self.end_time + timedelta(days=1)
        )
        
        swap_request = shifts.create_swap_request(
            original_shift_id=shift1.id,
            requested_by=self.staff_user1,
            requested_with=self.staff_user2,
            target_shift_id=shift2.id,
            reason="Personal emergency"
        )
        
        self.assertEqual(swap_request.original_shift, shift1)
        self.assertEqual(swap_request.target_shift, shift2)
        self.assertEqual(swap_request.requested_by, self.staff_user1)
        self.assertEqual(swap_request.requested_with, self.staff_user2)
        self.assertEqual(swap_request.status, ShiftSwapRequest.SwapStatus.PENDING)
    
    def test_get_staff_schedule(self):
        """Test getting staff schedule."""
        # Create multiple shifts for staff member
        shift1 = shifts.create(
            cluster=self.cluster,
            title="Shift 1",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        shift2 = shifts.create(
            cluster=self.cluster,
            title="Shift 2",
            shift_type=ShiftType.MAINTENANCE,
            assigned_staff=self.staff_user1,
            start_time=self.start_time + timedelta(days=1),
            end_time=self.end_time + timedelta(days=1)
        )
        
        # Create shift for different staff member (should not be included)
        shifts.create(
            cluster=self.cluster,
            title="Other Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user2,
            start_time=self.start_time + timedelta(days=2),
            end_time=self.end_time + timedelta(days=2)
        )
        
        schedule = shifts.get_staff_schedule(
            cluster=self.cluster,
            staff_member=self.staff_user1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7)
        )
        
        self.assertEqual(schedule.count(), 2)
        shift_ids = [shift.id for shift in schedule]
        self.assertIn(shift1.id, shift_ids)
        self.assertIn(shift2.id, shift_ids)
    
    def test_get_shift_statistics(self):
        """Test getting shift statistics."""
        # Create shifts with different statuses
        shift1 = shifts.create(
            cluster=self.cluster,
            title="Completed Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time,
            end_time=self.end_time
        )
        shift1.status = ShiftStatus.COMPLETED
        shift1.save()
        
        shift2 = shifts.create(
            cluster=self.cluster,
            title="No Show Shift",
            shift_type=ShiftType.MAINTENANCE,
            assigned_staff=self.staff_user2,
            start_time=self.start_time + timedelta(days=1),
            end_time=self.end_time + timedelta(days=1)
        )
        shift2.status = ShiftStatus.NO_SHOW
        shift2.save()
        
        shift3 = shifts.create(
            cluster=self.cluster,
            title="Cancelled Shift",
            shift_type=ShiftType.CLEANING,
            assigned_staff=self.staff_user1,
            start_time=self.start_time + timedelta(days=2),
            end_time=self.end_time + timedelta(days=2)
        )
        shift3.status = ShiftStatus.CANCELLED
        shift3.save()
        
        stats = shifts.get_statistics(self.cluster)
        
        self.assertEqual(stats['total_shifts'], 3)
        self.assertEqual(stats['completed_shifts'], 1)
        self.assertEqual(stats['no_show_shifts'], 1)
        self.assertEqual(stats['cancelled_shifts'], 1)
        self.assertEqual(stats['attendance_rate'], 33.33)  # 1/3 * 100


class ShiftNotificationManagerTest(TestCase):
    """Test cases for ShiftNotificationManager utility."""
    
    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Cluster",
            address="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.staff_user = AccountUser.objects.create_user(
            email_address="staff@test.com",
            name="Test Staff",
            phone_number="+1234567890",
            is_cluster_staff=True
        )
        self.staff_user.clusters.add(self.cluster)
        
        self.start_time = timezone.now() + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=8)
        
        self.shift = Shift.objects.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
    
    def test_send_shift_assignment_notification(self):
        """Test sending shift assignment notification."""
        # This test just verifies the method runs without error
        # In a real implementation, you would mock the email service
        result = shifts.send_assignment_notification(self.shift)
        self.assertTrue(result)
    
    def test_send_shift_reminder_notification(self):
        """Test sending shift reminder notification."""
        result = shifts.send_reminder_notification(self.shift)
        self.assertTrue(result)
    
    def test_send_missed_shift_notification(self):
        """Test sending missed shift notification."""
        result = shifts.send_missed_shift_notification(self.shift)
        self.assertTrue(result)
    
    def test_send_swap_request_notification(self):
        """Test sending swap request notification."""
        staff_user2 = AccountUser.objects.create_user(
            email_address="staff2@test.com",
            name="Test Staff 2",
            phone_number="+1234567891",
            is_cluster_staff=True
        )
        staff_user2.clusters.add(self.cluster)
        
        swap_request = ShiftSwapRequest.objects.create(
            cluster=self.cluster,
            original_shift=self.shift,
            requested_by=self.staff_user,
            requested_with=staff_user2,
            reason="Personal emergency"
        )
        
        result = shifts.send_swap_request_notification(swap_request)
        self.assertTrue(result)
    
    def test_send_swap_response_notification(self):
        """Test sending swap response notification."""
        staff_user2 = AccountUser.objects.create_user(
            email_address="staff2@test.com",
            name="Test Staff 2",
            phone_number="+1234567891",
            is_cluster_staff=True
        )
        staff_user2.clusters.add(self.cluster)
        
        admin_user = AccountUser.objects.create_user(
            email_address="admin@test.com",
            name="Test Admin",
            phone_number="+1234567892",
            is_cluster_admin=True
        )
        admin_user.clusters.add(self.cluster)
        
        swap_request = ShiftSwapRequest.objects.create(
            cluster=self.cluster,
            original_shift=self.shift,
            requested_by=self.staff_user,
            requested_with=staff_user2,
            reason="Personal emergency"
        )
        
        swap_request.approve(admin_user, "Approved")
        
        result = shifts.send_swap_response_notification(swap_request)
        self.assertTrue(result)