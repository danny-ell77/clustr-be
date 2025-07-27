import django_filters
from django.db.models import Q
from django.utils import timezone

from accounts.models import AccountUser, Role
from core.common.models import Shift, ShiftSwapRequest, Announcement, IssueTicket, Child, ExitRequest, EntryExitLog, MaintenanceLog, MaintenanceSchedule, Task, TaskComment, EmergencyContact, SOSAlert, EmergencyResponse, Event, EventGuest, Invitation, Visitor, VisitorLog


class UserFilter(django_filters.FilterSet):
    class Meta:
        model = AccountUser
        fields = []


class RoleFilter(django_filters.FilterSet):
    class Meta:
        model = Role
        fields = []


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


class ShiftSwapRequestFilter(django_filters.FilterSet):
    """Filter for shift swap requests"""
    status = django_filters.CharFilter(field_name='status')
    user_filter = django_filters.CharFilter(method='filter_user_involvement')

    class Meta:
        model = ShiftSwapRequest
        fields = ['status']

    def filter_user_involvement(self, queryset, name, value):
        user = self.request.user
        if value == 'my_requests':
            return queryset.filter(requested_by=user)
        elif value == 'requests_for_me':
            return queryset.filter(requested_with=user)
        return queryset


class ManagementAnnouncementFilter(django_filters.FilterSet):
    """Filter for management announcements"""
    category = django_filters.CharFilter(field_name='category')
    is_published = django_filters.BooleanFilter(field_name='is_published')
    include_expired = django_filters.BooleanFilter(method='filter_include_expired')
    
    class Meta:
        model = Announcement
        fields = ['category', 'is_published', 'include_expired']

    def filter_include_expired(self, queryset, name, value):
        if not value:
            now = timezone.now()
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now)
            )
        return queryset


class ManagementIssueTicketFilter(django_filters.FilterSet):
    """Filter for management issue tickets"""
    status = django_filters.CharFilter(field_name='status')
    type = django_filters.CharFilter(field_name='issue_type')
    priority = django_filters.CharFilter(field_name='priority')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = IssueTicket
        fields = ['status', 'type', 'priority', 'assigned_to', 'date_from', 'date_to', 'search']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(issue_no__icontains=value) |
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(reported_by__name__icontains=value)
        )


class ChildFilter(django_filters.FilterSet):
    parent_id = django_filters.NumberFilter(field_name='parent_id')

    class Meta:
        model = Child
        fields = ['parent_id']


class ExitRequestFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    expired = django_filters.BooleanFilter(method='filter_expired')

    class Meta:
        model = ExitRequest
        fields = ['status', 'expired']

    def filter_expired(self, queryset, name, value):
        if value:
            queryset = queryset.filter(
                status=ExitRequest.Status.PENDING,
                expires_at__lt=timezone.now()
            )
            # Mark them as expired
            queryset.update(status=ExitRequest.Status.EXPIRED)
        return queryset


class EntryExitLogFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    log_type = django_filters.CharFilter(field_name='log_type')
    
    class Meta:
        model = EntryExitLog
        fields = ['status', 'log_type']


class MaintenanceLogFilter(django_filters.FilterSet):
    maintenance_type = django_filters.CharFilter(field_name='maintenance_type')
    property_type = django_filters.CharFilter(field_name='property_type')
    status = django_filters.CharFilter(field_name='status')
    priority = django_filters.CharFilter(field_name='priority')
    property_location = django_filters.CharFilter(field_name='property_location', lookup_expr='icontains')
    equipment_name = django_filters.CharFilter(field_name='equipment_name', lookup_expr='icontains')
    performed_by = django_filters.NumberFilter(field_name='performed_by_id')
    date_from = django_filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at__date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = MaintenanceLog
        fields = [
            'maintenance_type', 'property_type', 'status', 'priority',
            'property_location', 'equipment_name', 'performed_by',
            'date_from', 'date_to', 'search'
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(maintenance_number__icontains=value) |
            Q(property_location__icontains=value) |
            Q(equipment_name__icontains=value)
        )


class MaintenanceScheduleFilter(django_filters.FilterSet):
    property_type = django_filters.CharFilter(field_name='property_type')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')

    class Meta:
        model = MaintenanceSchedule
        fields = ['property_type', 'is_active', 'assigned_to']


class TaskFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    priority = django_filters.CharFilter(field_name='priority')
    task_type = django_filters.CharFilter(field_name='task_type')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')
    created_by = django_filters.NumberFilter(field_name='created_by_id')
    search = django_filters.CharFilter(method='filter_search')
    user_id = django_filters.NumberFilter(method='filter_by_user')
    task_status = django_filters.CharFilter(method='filter_by_user_status')

    class Meta:
        model = Task
        fields = [
            'status', 'priority', 'task_type', 'assigned_to', 'created_by',
            'search', 'user_id', 'task_status'
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(task_number__icontains=value) |
            Q(location__icontains=value)
        )

    def filter_by_user(self, queryset, name, value):
        return queryset.filter(Q(assigned_to_id=value) | Q(created_by_id=value))

    def filter_by_user_status(self, queryset, name, value):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return queryset.filter(
                Q(assigned_to_id=user_id) | Q(created_by_id=user_id),
                status=value
            )
        return queryset


class TaskCommentFilter(django_filters.FilterSet):
    task_id = django_filters.NumberFilter(field_name='task_id')

    class Meta:
        model = TaskComment
        fields = ['task_id']


class EmergencyContactFilter(django_filters.FilterSet):
    contact_type = django_filters.CharFilter(field_name='contact_type')
    user_id = django_filters.NumberFilter(field_name='user_id')
    emergency_type = django_filters.CharFilter(method='filter_emergency_type')

    class Meta:
        model = EmergencyContact
        fields = ['contact_type', 'user_id', 'emergency_type']

    def filter_emergency_type(self, queryset, name, value):
        return queryset.filter(emergency_types__contains=[value])


class SOSAlertFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    emergency_type = django_filters.CharFilter(field_name='emergency_type')
    user_id = django_filters.NumberFilter(field_name='user_id')

    class Meta:
        model = SOSAlert
        fields = ['status', 'emergency_type', 'user_id']


class EmergencyResponseFilter(django_filters.FilterSet):
    alert_id = django_filters.NumberFilter(field_name='alert_id')
    responder_id = django_filters.NumberFilter(field_name='responder_id')

    class Meta:
        model = EmergencyResponse
        fields = ['alert_id', 'responder_id']


class EventFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    start_date = django_filters.DateFilter(field_name='start_time__date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='end_time__date', lookup_expr='lte')

    class Meta:
        model = Event
        fields = ['status', 'start_date', 'end_date']


class EventGuestFilter(django_filters.FilterSet):
    event_id = django_filters.NumberFilter(field_name='event_id')
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = EventGuest
        fields = ['event_id', 'status']


class InvitationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    created_by = django_filters.NumberFilter(field_name='created_by_id')

    class Meta:
        model = Invitation
        fields = ['status', 'created_by']


class VisitorFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    invited_by = django_filters.NumberFilter(field_name='invited_by_id')

    class Meta:
        model = Visitor
        fields = ['status', 'invited_by']


class VisitorLogFilter(django_filters.FilterSet):
    visitor = django_filters.NumberFilter(field_name='visitor_id')
    log_type = django_filters.CharFilter(field_name='log_type')

    class Meta:
        model = VisitorLog
        fields = ['visitor', 'log_type']
