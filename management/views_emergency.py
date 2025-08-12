"""
Emergency management views for management app.
"""

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import HasSpecificPermission
from core.common.models.emergency import (
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
    EmergencyStatus,
)
from core.common.serializers.emergency_serializers import (
    EmergencyContactSerializer,
    EmergencyContactCreateSerializer,
    EmergencyContactUpdateSerializer,
    SOSAlertSerializer,
    SOSAlertCreateSerializer,
    SOSAlertUpdateSerializer,
    EmergencyResponseSerializer,
    EmergencyResponseCreateSerializer,
    EmergencyTypeChoicesSerializer,
    EmergencyContactTypeChoicesSerializer,
    EmergencyStatusChoicesSerializer,
    EmergencyStatsSerializer,
    EmergencyReportSerializer,
    IncidentReportSerializer,
    EmergencyReportFiltersSerializer,
)
from core.common.includes import emergencies
from core.common.permissions import CommunicationsPermissions
from management.filters import EmergencyContactFilter, SOSAlertFilter, EmergencyResponseFilter


class EmergencyContactManagementViewSet(ModelViewSet):
    """
    ViewSet for managing all emergency contacts (personal and estate-wide).
    Management can view and manage all emergency contacts.
    """
    
    serializer_class = EmergencyContactSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ManageEmergencyContacts)
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmergencyContactFilter
    
    def get_queryset(self):
        """Get all emergency contacts for the cluster"""
        return EmergencyContact.objects.filter(
            cluster=getattr(self.request, "cluster_context", None)
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return EmergencyContactCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EmergencyContactUpdateSerializer
        return EmergencyContactSerializer
    
    def perform_create(self, serializer):
        """Create emergency contact"""
        serializer.save(
            
            created_by=self.request.user.id
        )
    
    def perform_update(self, serializer):
        """Update emergency contact"""
        serializer.save(last_modified_by=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def estate_wide(self, request):
        """Get estate-wide emergency contacts"""
        contacts = EmergencyContact.objects.filter(
            cluster=request.cluster_context,
            contact_type=EmergencyContactType.ESTATE_WIDE
        )
        
        emergency_type = request.query_params.get('emergency_type')
        if emergency_type:
            contacts = contacts.filter(emergency_types__contains=[emergency_type])
        
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get emergency contacts by emergency type"""
        emergency_type = request.query_params.get('emergency_type')
        if not emergency_type:
            return Response(
                {'error': _('emergency_type parameter is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contacts = emergencies.get_contacts_for_type(
            request.cluster_context,
            emergency_type
        )
        
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def emergency_types(self, request):
        """Get available emergency types"""
        choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EmergencyType.choices
        ]
        serializer = EmergencyTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def contact_types(self, request):
        """Get available contact types"""
        choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EmergencyContactType.choices
        ]
        serializer = EmergencyContactTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)


class SOSAlertManagementViewSet(ModelViewSet):
    """
    ViewSet for managing all SOS alerts.
    Management can view, acknowledge, respond to, and resolve all alerts.
    """
    
    serializer_class = SOSAlertSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ManageEmergency)
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SOSAlertFilter
    
    def get_queryset(self):
        """Get all SOS alerts for the cluster"""
        return SOSAlert.objects.filter(
            cluster=getattr(self.request, "cluster_context", None)
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return SOSAlertCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SOSAlertUpdateSerializer
        return SOSAlertSerializer
    
    def perform_create(self, serializer):
        """Create SOS alert on behalf of a user"""
        user_id = self.request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': _('user_id is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from accounts.models import AccountUser
        user = get_object_or_404(AccountUser, id=user_id, clusters=getattr(self.request, "cluster_context", None))
        
        alert = emergencies.create_alert(
            user=user,
            emergency_type=serializer.validated_data['emergency_type'],
            description=serializer.validated_data.get('description', ''),
            location=serializer.validated_data.get('location', ''),
            priority=serializer.validated_data.get('priority', 'high')
        )
        
        if not alert:
            return Response(
                {'error': _('Failed to create SOS alert')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return alert
    
    def perform_update(self, serializer):
        """Update SOS alert"""
        serializer.save(last_modified_by=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active alerts"""
        active_alerts = emergencies.get_active_alerts(request.cluster_context)
        serializer = self.get_serializer(active_alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an SOS alert"""
        alert = self.get_object()
        
        if emergencies.acknowledge_alert(alert, request.user):
            return Response({'message': _('Alert acknowledged successfully')})
        else:
            return Response(
                {'error': _('Failed to acknowledge alert')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def start_response(self, request, pk=None):
        """Start response to an SOS alert"""
        alert = self.get_object()
        
        if emergencies.start_response(alert, request.user):
            return Response({'message': _('Response started successfully')})
        else:
            return Response(
                {'error': _('Failed to start response')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an SOS alert"""
        alert = self.get_object()
        notes = request.data.get('notes', '')
        
        if emergencies.resolve_alert(alert, request.user, notes):
            return Response({'message': _('Alert resolved successfully')})
        else:
            return Response(
                {'error': _('Failed to resolve alert')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an SOS alert"""
        alert = self.get_object()
        reason = request.data.get('reason', 'Cancelled by management')
        
        if emergencies.cancel_alert(alert, request.user, reason):
            return Response({'message': _('Alert cancelled successfully')})
        else:
            return Response(
                {'error': _('Failed to cancel alert')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get emergency statistics"""
        stats = emergencies.get_statistics(request.cluster_context)
        serializer = EmergencyStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def emergency_types(self, request):
        """Get available emergency types"""
        choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EmergencyType.choices
        ]
        serializer = EmergencyTypeChoicesSerializer(choices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def status_choices(self, request):
        """Get available status choices"""
        choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EmergencyStatus.choices
        ]
        serializer = EmergencyStatusChoicesSerializer(choices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        """Get responses for a specific alert"""
        alert = self.get_object()
        responses = EmergencyResponse.objects.filter(
            cluster=request.cluster_context,
            alert=alert
        ).order_by('-created_at')
        
        serializer = EmergencyResponseSerializer(responses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Generate comprehensive emergency report"""
        # Validate filters
        filter_serializer = EmergencyReportFiltersSerializer(data=request.data)
        if not filter_serializer.is_valid():
            return Response(
                filter_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = filter_serializer.validated_data
        
        # Generate report
        report = emergencies.generate_report(
            cluster=request.cluster_context,
            start_date=filters.get('start_date'),
            end_date=filters.get('end_date'),
            emergency_type=filters.get('emergency_type'),
            status=filters.get('status')
        )
        
        serializer = EmergencyReportSerializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def incident_report(self, request, pk=None):
        """Generate detailed incident report for a specific alert"""
        alert = self.get_object()
        
        # Generate incident report
        report = emergencies.generate_incident_report(alert)
        
        serializer = IncidentReportSerializer(report)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export_report(self, request):
        """Export emergency report in various formats"""
        # Get report parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        emergency_type = request.query_params.get('emergency_type')
        status_filter = request.query_params.get('status')
        export_format = request.query_params.get('format', 'json')
        
        # Parse dates if provided
        from django.utils.dateparse import parse_datetime
        
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            parsed_start_date = parse_datetime(start_date)
            if not parsed_start_date:
                return Response(
                    {'error': _('Invalid start_date format')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            parsed_end_date = parse_datetime(end_date)
            if not parsed_end_date:
                return Response(
                    {'error': _('Invalid end_date format')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Generate report
        report = emergencies.generate_report(
            cluster=request.cluster_context,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            emergency_type=emergency_type,
            status=status_filter
        )
        
        # Handle different export formats
        if export_format.lower() == 'csv':
            return emergencies.export_report_as_csv(report)
        elif export_format.lower() == 'pdf':
            return emergencies.export_report_as_pdf(report)
        else:
            # Default to JSON
            serializer = EmergencyReportSerializer(report)
            return Response(serializer.data)


class EmergencyResponseManagementViewSet(ModelViewSet):
    """
    ViewSet for managing emergency responses.
    Management can create and view all emergency responses.
    """
    
    serializer_class = EmergencyResponseSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasSpecificPermission(CommunicationsPermissions.ManageEmergency)
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmergencyResponseFilter
    
    def get_queryset(self):
        """Get all emergency responses for the cluster"""
        return EmergencyResponse.objects.filter(
            cluster=getattr(self.request, "cluster_context", None)
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return EmergencyResponseCreateSerializer
        return EmergencyResponseSerializer
    
    def perform_create(self, serializer):
        """Create emergency response"""
        serializer.save(
            
            responder=self.request.user,
            created_by=self.request.user.id
        )
    
    def perform_update(self, serializer):
        """Update emergency response"""
        serializer.save(last_modified_by=self.request.user.id)