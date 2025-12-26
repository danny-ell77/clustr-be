"""
Resident management views for ClustR management app.
"""

import logging
import csv
from io import StringIO
from django.db import transaction
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import AccountUser
from accounts.permissions import IsClusterStaffOrAdmin
from core.common.decorators import audit_viewset
from core.common.responses import success_response, error_response
from core.common.models import Bill
from management.serializers_resident import (
    ResidentListSerializer,
    ResidentDetailSerializer,
    ResidentCreateUpdateSerializer,
    ApprovalStatusSerializer,
    ResidentStatsSerializer,
)

logger = logging.getLogger('clustr')


class ResidentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@audit_viewset(resource_type='resident')
class ResidentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClusterStaffOrAdmin]
    pagination_class = ResidentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['approved_by_admin', 'is_verified']
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AccountUser.objects.none()

        cluster = self.request.cluster_context
        return AccountUser.objects.filter(
            clusters=cluster,
            is_staff=False,
            is_superuser=False
        ).order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ResidentDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ResidentCreateUpdateSerializer
        return ResidentListSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['cluster'] = self.request.cluster_context
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email_address__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(unit_address__icontains=search)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Residents retrieved successfully"
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Resident details retrieved successfully"
        )
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cluster = request.cluster_context
        resident = serializer.save(
            is_owner=True,
            is_staff=False,
            is_superuser=False
        )
        resident.clusters.add(cluster)
        resident.primary_cluster = cluster
        resident.save()
        
        return success_response(
            data=ResidentListSerializer(resident, context={'cluster': cluster}).data,
            message="Resident created successfully",
            status_code=status.HTTP_201_CREATED
        )
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return success_response(
            data=ResidentListSerializer(instance, context={'cluster': request.cluster_context}).data,
            message="Resident updated successfully"
        )

    @action(detail=True, methods=['post'], url_path='update-approval-status')
    def update_approval_status(self, request, pk=None):
        resident = self.get_object()
        serializer = ApprovalStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        approved = serializer.validated_data['approved']
        resident.approved_by_admin = approved
        resident.save(update_fields=['approved_by_admin'])
        
        return success_response(
            data={'approved_by_admin': resident.approved_by_admin},
            message=f"Resident {'approved' if approved else 'rejected'} successfully"
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        cluster = request.cluster_context
        residents = AccountUser.objects.filter(
            clusters=cluster,
            is_staff=False,
            is_superuser=False
        )
        
        total_residents = residents.count()
        approved_residents = residents.filter(approved_by_admin=True).count()
        pending_approval = residents.filter(approved_by_admin=False).count()
        
        bills = Bill.objects.filter(cluster=cluster)
        total_bills = bills.count()
        paid_bills = bills.filter(paid_at__isnull=False).count()
        
        unpaid_bills = 0
        pending_bills = 0
        overdue_bills = 0
        
        for bill in bills:
            if not bill.is_fully_paid:
                if bill.is_overdue:
                    overdue_bills += 1
                else:
                    pending_bills += 1
        
        unpaid_bills = total_bills - paid_bills - pending_bills - overdue_bills
        
        stats_data = {
            'total_residents': total_residents,
            'approved_residents': approved_residents,
            'pending_approval': pending_approval,
            'total_bills': total_bills,
            'paid_bills': paid_bills,
            'unpaid_bills': unpaid_bills,
            'pending_bills': pending_bills,
            'overdue_bills': overdue_bills,
        }
        
        serializer = ResidentStatsSerializer(data=stats_data)
        serializer.is_valid()
        
        return success_response(
            data=serializer.data,
            message="Resident statistics retrieved successfully"
        )

    @action(detail=False, methods=['get'])
    def export(self, request):
        cluster = request.cluster_context
        residents = self.filter_queryset(self.get_queryset())
        
        search = request.query_params.get('search', None)
        if search:
            residents = residents.filter(
                Q(name__icontains=search) |
                Q(email_address__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(unit_address__icontains=search)
            )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="residents.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name',
            'Email',
            'Phone',
            'Unit Address',
            'Approval Status',
            'Verified',
            'Phone Verified',
            'Date Joined',
        ])
        
        for resident in residents:
            writer.writerow([
                resident.name,
                resident.email_address,
                resident.phone_number,
                resident.unit_address or '',
                'Approved' if resident.approved_by_admin else 'Pending',
                'Yes' if resident.is_verified else 'No',
                'Yes' if resident.is_phone_verified else 'No',
                resident.date_joined.strftime('%Y-%m-%d %H:%M:%S') if resident.date_joined else '',
            ])
        
        return response

    @action(detail=False, methods=['post'], url_path='import-csv')
    @transaction.atomic
    def import_csv(self, request):
        if 'file' not in request.FILES:
            return error_response(
                code="MISSING_FILE",
                message="No file provided",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        csv_file = request.FILES['file']
        
        if not csv_file.name.endswith('.csv'):
            return error_response(
                code="INVALID_FILE_TYPE",
                message="File must be a CSV",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            cluster = request.cluster_context
            created_count = 0
            updated_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    email = row.get('Email', '').strip()
                    if not email:
                        errors.append(f"Row {row_num}: Email is required")
                        continue
                    
                    name = row.get('Name', '').strip()
                    if not name:
                        errors.append(f"Row {row_num}: Name is required")
                        continue
                    
                    phone = row.get('Phone', '').strip()
                    unit_address = row.get('Unit Address', '').strip()
                    
                    resident, created = AccountUser.objects.get_or_create(
                        email_address=email,
                        defaults={
                            'name': name,
                            'phone_number': phone or '+2340000000000',
                            'unit_address': unit_address,
                            'is_owner': True,
                            'is_staff': False,
                            'is_superuser': False,
                        }
                    )
                    
                    if created:
                        resident.clusters.add(cluster)
                        resident.primary_cluster = cluster
                        resident.save()
                        created_count += 1
                    else:
                        resident.name = name
                        if phone:
                            resident.phone_number = phone
                        if unit_address:
                            resident.unit_address = unit_address
                        resident.save()
                        
                        if cluster not in resident.clusters.all():
                            resident.clusters.add(cluster)
                        
                        updated_count += 1
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return success_response(
                data={
                    'created': created_count,
                    'updated': updated_count,
                    'errors': errors,
                },
                message=f"Import completed: {created_count} created, {updated_count} updated"
            )
        
        except Exception as e:
            logger.error(f"CSV import error: {str(e)}")
            return error_response(
                code="IMPORT_ERROR",
                message=f"Failed to import CSV: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
