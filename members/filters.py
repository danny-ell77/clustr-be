import django_filters
from django.db.models import Q
from django.utils import timezone

from core.common.models import (
    Announcement, AnnouncementReadStatus, IssueTicket, IssueComment, 
    IssueAttachment, Child, ExitRequest, EntryExitLog, MaintenanceLog, 
    Visitor, VisitorLog, Transaction, Bill, RecurringPayment, EmergencyContact
)


class EmergencyContactFilter(django_filters.FilterSet):
    class Meta:
        model = EmergencyContact
        fields = []


class MemberAnnouncementFilter(django_filters.FilterSet):
    """Filter for member announcements"""
    category = django_filters.CharFilter(field_name='category')
    read_status = django_filters.CharFilter(method='filter_read_status')
    
    class Meta:
        model = Announcement
        fields = ['category', 'read_status']

    def filter_read_status(self, queryset, name, value):
        user = self.request.user
        if value == 'unread':
            read_announcement_ids = AnnouncementReadStatus.objects.filter(
                user_id=user.id,
                is_read=True
            ).values_list('announcement_id', flat=True)
            queryset = queryset.exclude(id__in=read_announcement_ids)
        elif value == 'read':
            read_announcement_ids = AnnouncementReadStatus.objects.filter(
                user_id=user.id,
                is_read=True
            ).values_list('announcement_id', flat=True)
            queryset = queryset.filter(id__in=read_announcement_ids)
        return queryset


class MembersIssueTicketFilter(django_filters.FilterSet):
    """Filter for members issue tickets"""
    status = django_filters.CharFilter(field_name='status')
    type = django_filters.CharFilter(field_name='issue_type')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = IssueTicket
        fields = ['status', 'type', 'date_from', 'date_to', 'search']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(issue_no__icontains=value) |
            Q(title__icontains=value) |
            Q(description__icontains=value)
        )


class MembersIssueCommentFilter(django_filters.FilterSet):
    issue_id = django_filters.NumberFilter(field_name='issue_id')

    class Meta:
        model = IssueComment
        fields = ['issue_id']


class MembersIssueAttachmentFilter(django_filters.FilterSet):
    issue_id = django_filters.NumberFilter(field_name='issue_id')
    comment_id = django_filters.NumberFilter(field_name='comment_id')

    class Meta:
        model = IssueAttachment
        fields = ['issue_id', 'comment_id']


class MemberChildFilter(django_filters.FilterSet):
    class Meta:
        model = Child
        fields = []


class MemberExitRequestFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = ExitRequest
        fields = ['status']


class MemberEntryExitLogFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    log_type = django_filters.CharFilter(field_name='log_type')

    class Meta:
        model = EntryExitLog
        fields = ['status', 'log_type']


class MemberMaintenanceLogFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    maintenance_type = django_filters.CharFilter(field_name='maintenance_type')
    date_from = django_filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at__date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = MaintenanceLog
        fields = ['status', 'maintenance_type', 'date_from', 'date_to', 'search']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(maintenance_number__icontains=value) |
            Q(property_location__icontains=value) |
            Q(equipment_name__icontains=value)
        )


class MemberMaintenanceHistoryFilter(django_filters.FilterSet):
    property_location = django_filters.CharFilter(field_name='property_location', lookup_expr='icontains')
    equipment_name = django_filters.CharFilter(field_name='equipment_name', lookup_expr='icontains')

    class Meta:
        model = MaintenanceLog
        fields = ['property_location', 'equipment_name']


class MemberVisitorFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = Visitor
        fields = ['status']


class MemberVisitorLogFilter(django_filters.FilterSet):
    log_type = django_filters.CharFilter(field_name='log_type')

    class Meta:
        model = VisitorLog
        fields = ['log_type']

# Payment-related filters
class TransactionFilter(django_filters.FilterSet):
    """Filter for user transactions"""
    type = django_filters.CharFilter(field_name='type')
    status = django_filters.CharFilter(field_name='status')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    provider = django_filters.CharFilter(field_name='provider')
    
    class Meta:
        model = Transaction
        fields = ['type', 'status', 'date_from', 'date_to', 'amount_min', 'amount_max', 'provider']


class BillFilter(django_filters.FilterSet):
    """Filter for user bills"""
    status = django_filters.CharFilter(field_name='status')
    type = django_filters.CharFilter(field_name='type')
    due_date_from = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    due_date_to = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    is_overdue = django_filters.BooleanFilter(method='filter_overdue')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Bill
        fields = ['status', 'type', 'due_date_from', 'due_date_to', 'amount_min', 'amount_max', 'is_overdue', 'search']
    
    def filter_overdue(self, queryset, name, value):
        if value is True:
            return queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'acknowledged'])
        elif value is False:
            return queryset.exclude(due_date__lt=timezone.now(), status__in=['pending', 'acknowledged'])
        return queryset
    
    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(bill_number__icontains=value) |
            Q(title__icontains=value) |
            Q(description__icontains=value)
        )


class RecurringPaymentFilter(django_filters.FilterSet):
    """Filter for user recurring payments"""
    status = django_filters.CharFilter(field_name='status')
    frequency = django_filters.CharFilter(field_name='frequency')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    start_date_from = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    bill_id = django_filters.UUIDFilter(field_name='bill__id')
    bill_type = django_filters.CharFilter(field_name='bill__type')
    bill_status = django_filters.CharFilter(field_name='bill__status')
    utility_provider = django_filters.UUIDFilter(field_name='utility_provider__id')
    payment_source = django_filters.CharFilter(field_name='payment_source')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = RecurringPayment
        fields = [
            'status', 'frequency', 'amount_min', 'amount_max', 
            'start_date_from', 'start_date_to', 'bill_id', 'bill_type', 
            'bill_status', 'utility_provider', 'payment_source', 'search'
        ]
    
    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(bill__title__icontains=value) |
            Q(customer_id__icontains=value) |
            Q(utility_provider__name__icontains=value)
        )