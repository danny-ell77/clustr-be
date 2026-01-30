"""
Staff management views for ClustR management app.
"""

import logging
from django.core.exceptions import ValidationError
from django.db import models
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from core.common.decorators import audit_viewset
from core.common.models import Staff, Shift, ShiftStatus
from core.common.serializers.shift_serializers import StaffSerializer, ShiftListSerializer
from accounts.permissions import IsClusterStaffOrAdmin, IsClusterAdmin

logger = logging.getLogger('clustr')


class StaffFilter(django_filters.FilterSet):
    """Filter for staff members"""
    staff_type = django_filters.CharFilter(field_name='staff_type')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Staff
        fields = ['staff_type', 'is_active']
    
    def filter_search(self, queryset, name, value):
        """Search across name, email, phone, and employee_id"""
        return queryset.filter(
            models.Q(name__icontains=value) |
            models.Q(email__icontains=value) |
            models.Q(phone_number__icontains=value) |
            models.Q(employee_id__icontains=value)
        )



@audit_viewset(resource_type='staff')
class StaffViewSet(ModelViewSet):
    """
    ViewSet for managing staff members.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsClusterStaffOrAdmin]
    serializer_class = StaffSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StaffFilter
    
    def get_queryset(self):
        """Get staff for the current cluster."""
        if getattr(self, "swagger_fake_view", False):
            return Staff.objects.none()

        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            return Staff.objects.none()
        
        return Staff.objects.filter(cluster=cluster).order_by('name')
    
    def perform_create(self, serializer):
        """Create a new staff member."""
        cluster = getattr(self.request, 'cluster_context', None)
        if not cluster:
            raise ValidationError("Cluster context is required")
        
        serializer.save(
            cluster=cluster,
            created_by=self.request.user.id,
            last_modified_by=self.request.user.id
        )
    
    def perform_update(self, serializer):
        """Update a staff member."""
        serializer.save(last_modified_by=self.request.user.id)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a staff member."""
        staff = self.get_object()
        staff.is_active = False
        staff.last_modified_by = request.user.id
        staff.save(update_fields=['is_active', 'last_modified_by', 'last_modified_at'])
        
        return Response({
            'message': 'Staff member deactivated successfully',
            'staff': StaffSerializer(staff).data
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a staff member."""
        staff = self.get_object()
        staff.is_active = True
        staff.last_modified_by = request.user.id
        staff.save(update_fields=['is_active', 'last_modified_by', 'last_modified_at'])
        
        return Response({
            'message': 'Staff member activated successfully',
            'staff': StaffSerializer(staff).data
        })
    
    @action(detail=True, methods=['get'])
    def shifts(self, request, pk=None):
        """Get all shifts for a staff member."""
        staff = self.get_object()
        
        # Parse query parameters
        status_filter = request.query_params.get('status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        shifts = Shift.objects.filter(
            cluster=staff.cluster,
            assigned_staff=staff
        )
        
        if status_filter:
            shifts = shifts.filter(status=status_filter)
        if start_date:
            shifts = shifts.filter(start_time__date__gte=start_date)
        if end_date:
            shifts = shifts.filter(end_time__date__lte=end_date)
        
        shifts = shifts.select_related('attendance').order_by('-start_time')
        serializer = ShiftListSerializer(shifts, many=True)
        
        return Response({
            'staff': StaffSerializer(staff).data,
            'shifts': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get staff statistics."""
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_staff = Staff.objects.filter(cluster=cluster).count()
        active_staff = Staff.objects.filter(cluster=cluster, is_active=True).count()
        
        # Count by staff type
        from django.db.models import Count
        by_type = Staff.objects.filter(cluster=cluster, is_active=True).values('staff_type').annotate(count=Count('id'))
        
        return Response({
            'total_staff': total_staff,
            'active_staff': active_staff,
            'inactive_staff': total_staff - active_staff,
            'by_type': {item['staff_type']: item['count'] for item in by_type}
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsClusterAdmin])
    def export(self, request):
        """Export staff list to CSV."""
        import csv
        from django.http import HttpResponse
        
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return Response(
                {'error': 'Cluster context is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        staff_members = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="staff_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Phone', 'Staff Type', 'Employee ID', 'Active', 'Date Joined'])
        
        for staff in staff_members:
            writer.writerow([
                staff.name,
                staff.email or '',
                staff.phone_number,
                staff.get_staff_type_display(),
                staff.employee_id or '',
                'Yes' if staff.is_active else 'No',
                staff.date_joined.strftime('%Y-%m-%d')
            ])
        
        return response
