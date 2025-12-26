"""
Shift management views for ClustR management app.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from management.filters import ShiftFilter, ShiftSwapRequestFilter

from core.common.decorators import audit_viewset
from core.common.models import Shift, ShiftSwapRequest, ShiftAttendance, ShiftStatus
from core.common.serializers.shift_serializers import (
    ShiftSerializer,
    ShiftCreateSerializer,
    ShiftUpdateSerializer,
    ShiftListSerializer,
    ShiftSwapRequestSerializer,
    ShiftSwapRequestCreateSerializer,
    ShiftSwapResponseSerializer,
    ClockInOutSerializer,
    ShiftStatisticsSerializer
)
from core.common.includes import notifications, shifts
from accounts.permissions import IsClusterStaffOrAdmin, IsClusterAdmin
from accounts.models import AccountUser

logger = logging.getLogger('clustr')


class ShiftFilter(django_filters.FilterSet):
    """Filter for shifts"""
    staff_id = django_filters.NumberFilter(field_name='assigned_staff_id')
    status = django_filters.CharFilter(field_name='status')
    shift_type = django_filters.CharFilter(field_name='shift_type')
    start_date = django_filters.DateFilter(field_name='start_time__date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='start_time__date', lookup_expr='lte')
    
    class Meta:
        model = Shift
        fields = ['staff_id', 'status', 'shift_type', 'start_date', 'end_date']


@audit_viewset(resource_type='shift')
class ShiftViewSet(ModelViewSet):
    """
    ViewSet for managing shifts.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ShiftFilter
    
    def get_queryset(self):
        """Get shifts for the current cluster."""
        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            return Shift.objects.none()
        
        queryset = Shift.objects.filter(cluster=cluster).select_related(
            'assigned_staff', 'attendance'
        )
        
        return queryset.order_by('-start_time')
    
    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return ShiftListSerializer
        elif self.action == 'create':
            return ShiftCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ShiftUpdateSerializer
        return ShiftSerializer
    
    def perform_create(self, serializer):
        """Create a new shift."""
        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            raise ValidationError("Cluster context is required")
        
        try:
            shift = shifts.create(
                cluster=cluster,
                created_by=self.request.user.id,
                last_modified_by=self.request.user.id,
                **serializer.validated_data
            )
            serializer.instance = shift
        except ValidationError as e:
            raise ValidationError(str(e))
    
    def perform_update(self, serializer):
        """Update a shift."""
        # Check for conflicts when updating
        if 'assigned_staff' in serializer.validated_data or 'start_time' in serializer.validated_data or 'end_time' in serializer.validated_data:
            assigned_staff = serializer.validated_data.get('assigned_staff', serializer.instance.assigned_staff)
            start_time = serializer.validated_data.get('start_time', serializer.instance.start_time)
            end_time = serializer.validated_data.get('end_time', serializer.instance.end_time)
            
            conflicts = shifts.check_conflicts(
                cluster=serializer.instance.cluster,
                staff_member=assigned_staff,
                start_time=start_time,
                end_time=end_time,
                exclude_shift_id=serializer.instance.id
            )
            
            if conflicts:
                conflict_details = [
                    f"{shift.title} ({shift.start_time.strftime('%Y-%m-%d %H:%M')} - {shift.end_time.strftime('%H:%M')})"
                    for shift in conflicts
                ]
                raise ValidationError(f"Shift conflicts detected with: {', '.join(conflict_details)}")
        
        serializer.save(last_modified_by=self.request.user.id)
    
    @action(detail=True, methods=['post'])
    def clock_in(self, request, pk=None):
        """Clock in a staff member for their shift."""
        shift = self.get_object()
        serializer = ClockInOutSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                clock_in_time = serializer.validated_data.get('timestamp')
                updated_shift = shifts.clock_in(shift, clock_in_time)
                
                return Response({
                    'message': 'Successfully clocked in',
                    'shift': ShiftSerializer(updated_shift).data
                })
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        """Clock out a staff member from their shift."""
        shift = self.get_object()
        serializer = ClockInOutSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                clock_out_time = serializer.validated_data.get('timestamp')
                updated_shift = shifts.clock_out(shift, clock_out_time)
                
                return Response({
                    'message': 'Successfully clocked out',
                    'shift': ShiftSerializer(updated_shift).data
                })
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_no_show(self, request, pk=None):
        """Mark a shift as no show."""
        shift = self.get_object()
        
        try:
            shift.mark_no_show()
            shifts.send_missed_shift_notification(shift)
            
            return Response({
                'message': 'Shift marked as no show',
                'shift': ShiftSerializer(shift).data
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a shift."""
        shift = self.get_object()
        
        try:
            shift.cancel()
            
            return Response({
                'message': 'Shift cancelled successfully',
                'shift': ShiftSerializer(shift).data
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get shift statistics."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            if start_date:
                start_date = datetime.fromisoformat(start_date).date()
            if end_date:
                end_date = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stats = shifts.get_statistics(cluster, start_date, end_date)
        serializer = ShiftStatisticsSerializer(stats)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming shifts."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        now = timezone.now()
        upcoming_shifts = Shift.objects.filter(
            cluster=cluster,
            status=ShiftStatus.SCHEDULED,
            start_time__gte=now,
            start_time__lte=now + timedelta(hours=24)
        ).select_related('assigned_staff').order_by('start_time')
        
        serializer = ShiftListSerializer(upcoming_shifts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue shifts."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        now = timezone.now()
        overdue_shifts = Shift.objects.filter(
            cluster=cluster,
            status__in=[ShiftStatus.SCHEDULED, ShiftStatus.IN_PROGRESS],
            end_time__lt=now
        ).select_related('assigned_staff').order_by('-end_time')
        
        serializer = ShiftListSerializer(overdue_shifts, many=True)
        return Response(serializer.data)


class ShiftSwapRequestFilter(django_filters.FilterSet):
    """Filter for shift swap requests"""
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = ShiftSwapRequest
        fields = ['status']


@audit_viewset(resource_type='shift_swap_request')
class ShiftSwapRequestViewSet(ModelViewSet):
    """
    ViewSet for managing shift swap requests.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShiftSwapRequestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ShiftSwapRequestFilter
    
    def get_queryset(self):
        """Get swap requests for the current cluster."""
        if getattr(self, "swagger_fake_view", False):
            return ShiftSwapRequest.objects.none()

        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            return ShiftSwapRequest.objects.none()

        queryset = ShiftSwapRequest.objects.filter(
            cluster=cluster
        ).select_related(
            'original_shift',
            'target_shift',
            'requested_by',
            'requested_with',
            'approved_by'
        )

        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return ShiftSwapRequestCreateSerializer
        return ShiftSwapRequestSerializer
    
    def perform_create(self, serializer):
        """Create a new swap request."""
        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            raise ValidationError("Cluster context is required")
        
        try:
            swap_request = shifts.create_swap_request(
                original_shift_id=serializer.validated_data['original_shift'].id,
                requested_by=self.request.user,
                requested_with=serializer.validated_data['requested_with'],
                target_shift_id=serializer.validated_data.get('target_shift').id if serializer.validated_data.get('target_shift') else None,
                reason=serializer.validated_data.get('reason', '')
            )
            serializer.instance = swap_request
        except ValidationError as e:
            raise ValidationError(str(e))
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to a swap request (approve/reject)."""
        swap_request = self.get_object()
        serializer = ShiftSwapResponseSerializer(data=request.data)
        
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            response_message = serializer.validated_data.get('response_message', '')
            
            try:
                if action_type == 'approve':
                    swap_request.approve(request.user, response_message)
                else:
                    swap_request.reject(request.user, response_message)
                
                # Send notification
                shifts.send_swap_response_notification(swap_request)
                
                return Response({
                    'message': f'Swap request {action_type}d successfully',
                    'swap_request': ShiftSwapRequestSerializer(swap_request).data
                })
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffScheduleView(APIView):
    """
    View for getting staff schedules.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    
    def get(self, request, staff_id=None):
        """Get schedule for a specific staff member or all staff."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            if start_date:
                start_date = datetime.fromisoformat(start_date).date()
            if end_date:
                end_date = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if staff_id:
            # Get schedule for specific staff member
            try:
                staff_member = AccountUser.objects.get(id=staff_id, clusters_in=[cluster])
            except AccountUser.DoesNotExist:
                return Response(
                    {'error': 'Staff member not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            shifts = shifts.get_staff_schedule(cluster, staff_member, start_date, end_date)
            serializer = ShiftListSerializer(shifts, many=True)
            
            return Response({
                'staff_member': {
                    'id': staff_member.id,
                    'name': staff_member.name,
                    'email': staff_member.email_address
                },
                'shifts': serializer.data
            })
        else:
            # Get schedule for all staff
            staff_members = AccountUser.objects.filter(
                clusters=[cluster],
                is_cluster_staff=True
            )
            
            schedules = []
            for staff_member in staff_members:
                shifts = shifts.get_staff_schedule(cluster, staff_member, start_date, end_date)
                schedules.append({
                    'staff_member': {
                        'id': staff_member.id,
                        'name': staff_member.name,
                        'email': staff_member.email_address
                    },
                    'shifts': ShiftListSerializer(shifts, many=True).data
                })
            
            return Response({'schedules': schedules})


class ShiftReportView(APIView):
    """
    View for generating shift reports.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterAdmin]
    
    def get(self, request):
        """Generate shift report."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        report_type = request.query_params.get('type', 'summary')
        
        try:
            if start_date:
                start_date = datetime.fromisoformat(start_date).date()
            if end_date:
                end_date = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if report_type == 'summary':
            # Generate summary report
            stats = shifts.get_statistics(cluster, start_date, end_date)
            
            # Get additional data
            shifts = Shift.objects.filter(cluster=cluster)
            if start_date:
                shifts = shifts.filter(start_time__date__gte=start_date)
            if end_date:
                shifts = shifts.filter(start_time__date__lte=end_date)
            
            # Group by staff member
            staff_stats = {}
            for shift in shifts.select_related('assigned_staff'):
                staff_name = shift.assigned_staff.name
                if staff_name not in staff_stats:
                    staff_stats[staff_name] = {
                        'total_shifts': 0,
                        'completed_shifts': 0,
                        'no_show_shifts': 0,
                        'cancelled_shifts': 0
                    }
                
                staff_stats[staff_name]['total_shifts'] += 1
                if shift.status == ShiftStatus.COMPLETED:
                    staff_stats[staff_name]['completed_shifts'] += 1
                elif shift.status == ShiftStatus.NO_SHOW:
                    staff_stats[staff_name]['no_show_shifts'] += 1
                elif shift.status == ShiftStatus.CANCELLED:
                    staff_stats[staff_name]['cancelled_shifts'] += 1
            
            return Response({
                'overall_statistics': stats,
                'staff_statistics': staff_stats,
                'period': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            })
        
        elif report_type == 'detailed':
            # Generate detailed report
            shifts = Shift.objects.filter(cluster=cluster).select_related(
                'assigned_staff', 'attendance'
            )
            
            if start_date:
                shifts = shifts.filter(start_time__date__gte=start_date)
            if end_date:
                shifts = shifts.filter(start_time__date__lte=end_date)
            
            serializer = ShiftSerializer(shifts.order_by('-start_time'), many=True)
            
            return Response({
                'shifts': serializer.data,
                'period': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            })
        
        else:
            return Response(
                {'error': 'Invalid report type. Use "summary" or "detailed"'},
                status=status.HTTP_400_BAD_REQUEST
            )