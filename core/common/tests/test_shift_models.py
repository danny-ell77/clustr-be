"""
Tests for shift models in ClustR application.
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.common.models import Cluster, Shift, ShiftSwapRequest, ShiftAttendance, ShiftType, ShiftStatus
from accounts.models import AccountUser


class ShiftModelTest(TestCase):
    """Test cases for Shift model."""
    
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
    
    def test_create_shift(self):
        """Test creating a shift."""
        shift = Shift.objects.create(
            cluster=self.cluster,
            title="Security Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time,
            location="Main Gate",
            responsibilities="Monitor entrance and exit"
        )
        
        self.assertEqual(shift.title, "Security Shift")
        self.assertEqual(shift.shift_type, ShiftType.SECURITY)
        self.assertEqual(shift.assigned_staff, self.staff_user)
        self.assertEqual(shift.status, ShiftStatus.SCHEDULED)
        self.assertFalse(shift.is_overdue)
        self.assertFalse(shift.is_upcoming)
    
    def test_shift_duration(self):
        """Test shift duration calculation."""
        shift = Shift.objects.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        expected_duration = self.end_time - self.start_time
        self.assertEqual(shift.duration, expected_duration)
    
    def test_shift_validation_start_before_end(self):
        """Test that start time must be before end time."""
        with self.assertRaises(ValidationError):
            shift = Shift(
                cluster=self.cluster,
                title="Invalid Shift",
                shift_type=ShiftType.SECURITY,
                assigned_staff=self.staff_user,
                start_time=self.end_time,  # Start after end
                end_time=self.start_time
            )
            shift.full_clean()
    
    def test_shift_overlap_validation(self):
        """Test that overlapping shifts are not allowed."""
        # Create first shift
        Shift.objects.create(
            cluster=self.cluster,
            title="First Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # Try to create overlapping shift
        with self.assertRaises(ValidationError):
            overlapping_shift = Shift(
                cluster=self.cluster,
                title="Overlapping Shift",
                shift_type=ShiftType.MAINTENANCE,
                assigned_staff=self.staff_user,
                start_time=self.start_time + timedelta(hours=2),  # Overlaps with first shift
                end_time=self.end_time + timedelta(hours=2)
            )
            overlapping_shift.full_clean()
    
    def test_clock_in_out(self):
        """Test clock in and clock out functionality."""
        shift = Shift.objects.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # Test clock in
        clock_in_time = timezone.now()
        shift.clock_in(clock_in_time)
        
        self.assertEqual(shift.status, ShiftStatus.IN_PROGRESS)
        self.assertEqual(shift.actual_start_time, clock_in_time)
        
        # Test clock out
        clock_out_time = clock_in_time + timedelta(hours=8)
        shift.clock_out(clock_out_time)
        
        self.assertEqual(shift.status, ShiftStatus.COMPLETED)
        self.assertEqual(shift.actual_end_time, clock_out_time)
    
    def test_mark_no_show(self):
        """Test marking shift as no show."""
        shift = Shift.objects.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        shift.mark_no_show()
        self.assertEqual(shift.status, ShiftStatus.NO_SHOW)
    
    def test_cancel_shift(self):
        """Test cancelling a shift."""
        shift = Shift.objects.create(
            cluster=self.cluster,
            title="Test Shift",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        shift.cancel()
        self.assertEqual(shift.status, ShiftStatus.CANCELLED)


class ShiftSwapRequestTest(TestCase):
    """Test cases for ShiftSwapRequest model."""
    
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
        
        self.admin_user = AccountUser.objects.create_user(
            email_address="admin@test.com",
            name="Test Admin",
            phone_number="+1234567892",
            is_cluster_admin=True
        )
        self.admin_user.clusters.add(self.cluster)
        
        self.start_time1 = timezone.now() + timedelta(hours=1)
        self.end_time1 = self.start_time1 + timedelta(hours=8)
        
        self.start_time2 = timezone.now() + timedelta(days=1)
        self.end_time2 = self.start_time2 + timedelta(hours=8)
        
        self.shift1 = Shift.objects.create(
            cluster=self.cluster,
            title="Shift 1",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user1,
            start_time=self.start_time1,
            end_time=self.end_time1
        )
        
        self.shift2 = Shift.objects.create(
            cluster=self.cluster,
            title="Shift 2",
            shift_type=ShiftType.SECURITY,
            assigned_staff=self.staff_user2,
            start_time=self.start_time2,
            end_time=self.end_time2
        )
    
    def test_create_swap_request(self):
        """Test creating a swap request."""
        swap_request = ShiftSwapRequest.objects.create(
            cluster=self.cluster,
            original_shift=self.shift1,
            requested_by=self.staff_user1,
            requested_with=self.staff_user2,
            target_shift=self.shift2,
            reason="Personal emergency"
        )
        
        self.assertEqual(swap_request.status, ShiftSwapRequest.SwapStatus.PENDING)
        self.assertEqual(swap_request.original_shift, self.shift1)
        self.assertEqual(swap_request.requested_by, self.staff_user1)
        self.assertEqual(swap_request.requested_with, self.staff_user2)
        self.assertEqual(swap_request.target_shift, self.shift2)
    
    def test_approve_swap_request(self):
        """Test approving a swap request."""
        swap_request = ShiftSwapRequest.objects.create(
            cluster=self.cluster,
            original_shift=self.shift1,
            requested_by=self.staff_user1,
            requested_with=self.staff_user2,
            target_shift=self.shift2,
            reason="Personal emergency"
        )
        
        swap_request.approve(self.admin_user, "Approved due to emergency")
        
        self.assertEqual(swap_request.status, ShiftSwapRequest.SwapStatus.APPROVED)
        self.assertEqual(swap_request.approved_by, self.admin_user)
        self.assertIsNotNone(swap_request.approved_at)
        
        # Check that shifts were swapped
        self.shift1.refresh_from_db()
        self.shift2.refresh_from_db()
        
        self.assertEqual(self.shift1.assigned_staff, self.staff_user2)
        self.assertEqual(self.shift2.assigned_staff, self.staff_user1)
    
    def test_reject_swap_request(self):
        """Test rejecting a swap request."""
        swap_request = ShiftSwapRequest.objects.create(
            cluster=self.cluster,
            original_shift=self.shift1,
            requested_by=self.staff_user1,
            requested_with=self.staff_user2,
            target_shift=self.shift2,
            reason="Personal emergency"
        )
        
        swap_request.reject(self.admin_user, "Not enough coverage")
        
        self.assertEqual(swap_request.status, ShiftSwapRequest.SwapStatus.REJECTED)
        self.assertEqual(swap_request.approved_by, self.admin_user)
        self.assertIsNotNone(swap_request.approved_at)
        
        # Check that shifts were not swapped
        self.shift1.refresh_from_db()
        self.shift2.refresh_from_db()
        
        self.assertEqual(self.shift1.assigned_staff, self.staff_user1)
        self.assertEqual(self.shift2.assigned_staff, self.staff_user2)


class ShiftAttendanceTest(TestCase):
    """Test cases for ShiftAttendance model."""
    
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
    
    def test_create_attendance(self):
        """Test creating attendance record."""
        attendance = ShiftAttendance.objects.create(
            cluster=self.cluster,
            shift=self.shift
        )
        
        self.assertEqual(attendance.shift, self.shift)
        self.assertEqual(attendance.total_break_duration, timedelta(0))
        self.assertEqual(attendance.overtime_hours, timedelta(0))
    
    def test_calculate_overtime(self):
        """Test overtime calculation."""
        attendance = ShiftAttendance.objects.create(
            cluster=self.cluster,
            shift=self.shift,
            clock_in_time=self.start_time,
            clock_out_time=self.end_time + timedelta(hours=2)  # 2 hours overtime
        )
        
        attendance.calculate_overtime()
        
        expected_overtime = timedelta(hours=2)
        self.assertEqual(attendance.overtime_hours, expected_overtime)
    
    def test_calculate_late_arrival(self):
        """Test late arrival calculation."""
        late_clock_in = self.start_time + timedelta(minutes=30)
        
        attendance = ShiftAttendance.objects.create(
            cluster=self.cluster,
            shift=self.shift,
            clock_in_time=late_clock_in
        )
        
        attendance.calculate_late_arrival()
        
        self.assertEqual(attendance.late_arrival_minutes, 30)
    
    def test_calculate_early_departure(self):
        """Test early departure calculation."""
        early_clock_out = self.end_time - timedelta(minutes=45)
        
        attendance = ShiftAttendance.objects.create(
            cluster=self.cluster,
            shift=self.shift,
            clock_out_time=early_clock_out
        )
        
        attendance.calculate_early_departure()
        
        self.assertEqual(attendance.early_departure_minutes, 45)
    
    def test_actual_work_duration(self):
        """Test actual work duration calculation."""
        clock_in_time = self.start_time
        clock_out_time = self.end_time
        break_duration = timedelta(minutes=30)
        
        attendance = ShiftAttendance.objects.create(
            cluster=self.cluster,
            shift=self.shift,
            clock_in_time=clock_in_time,
            clock_out_time=clock_out_time,
            total_break_duration=break_duration
        )
        
        expected_work_duration = (clock_out_time - clock_in_time) - break_duration
        self.assertEqual(attendance.actual_work_duration, expected_work_duration)