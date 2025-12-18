"""
Resident management serializers for ClustR management app.
"""

from rest_framework import serializers
from accounts.models import AccountUser
from core.common.models import Bill


class BillsSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    paid = serializers.IntegerField()
    unpaid = serializers.IntegerField()
    pending = serializers.IntegerField()
    overdue = serializers.IntegerField()


class ResidentListSerializer(serializers.ModelSerializer):
    bills_summary = serializers.SerializerMethodField()
    property_type = serializers.CharField(source='unit_address', allow_null=True)
    apartment_status = serializers.SerializerMethodField()
    approval_status = serializers.BooleanField(source='approved_by_admin')
    
    class Meta:
        model = AccountUser
        fields = [
            'id',
            'name',
            'email_address',
            'phone_number',
            'unit_address',
            'property_type',
            'apartment_status',
            'approval_status',
            'approved_by_admin',
            'is_verified',
            'is_phone_verified',
            'profile_image_url',
            'date_joined',
            'bills_summary',
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_bills_summary(self, obj):
        cluster = self.context.get('cluster')
        if not cluster:
            return {'total': 0, 'paid': 0, 'unpaid': 0, 'pending': 0, 'overdue': 0}
        
        bills = Bill.objects.filter(cluster=cluster, user_id=obj.id)
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
            else:
                unpaid_bills = total_bills - paid_bills - pending_bills - overdue_bills
        
        return {
            'total': total_bills,
            'paid': paid_bills,
            'unpaid': unpaid_bills,
            'pending': pending_bills,
            'overdue': overdue_bills,
        }
    
    def get_apartment_status(self, obj):
        if obj.unit_address:
            return 'OCCUPIED'
        return 'VACANT'


class ResidentDetailSerializer(serializers.ModelSerializer):
    bills = serializers.SerializerMethodField()
    bills_summary = serializers.SerializerMethodField()
    property_type = serializers.CharField(source='unit_address', allow_null=True)
    apartment_status = serializers.SerializerMethodField()
    approval_status = serializers.BooleanField(source='approved_by_admin')
    
    class Meta:
        model = AccountUser
        fields = [
            'id',
            'name',
            'email_address',
            'phone_number',
            'unit_address',
            'property_type',
            'apartment_status',
            'approval_status',
            'approved_by_admin',
            'is_verified',
            'is_phone_verified',
            'profile_image_url',
            'date_joined',
            'last_login',
            'bills_summary',
            'bills',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_bills_summary(self, obj):
        cluster = self.context.get('cluster')
        if not cluster:
            return {'total': 0, 'paid': 0, 'unpaid': 0, 'pending': 0, 'overdue': 0}
        
        bills = Bill.objects.filter(cluster=cluster, user_id=obj.id)
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
            else:
                unpaid_bills = total_bills - paid_bills - pending_bills - overdue_bills
        
        return {
            'total': total_bills,
            'paid': paid_bills,
            'unpaid': unpaid_bills,
            'pending': pending_bills,
            'overdue': overdue_bills,
        }
    
    def get_apartment_status(self, obj):
        if obj.unit_address:
            return 'OCCUPIED'
        return 'VACANT'
    
    def get_bills(self, obj):
        cluster = self.context.get('cluster')
        if not cluster:
            return []
        
        bills = Bill.objects.filter(cluster=cluster, user_id=obj.id).order_by('-created_at')
        
        return [{
            'id': str(bill.id),
            'bill_number': bill.bill_number,
            'title': bill.title,
            'description': bill.description,
            'type': bill.type,
            'amount': str(bill.amount),
            'currency': bill.currency,
            'due_date': bill.due_date.isoformat() if bill.due_date else None,
            'paid_amount': str(bill.paid_amount),
            'paid_at': bill.paid_at.isoformat() if bill.paid_at else None,
            'is_fully_paid': bill.is_fully_paid,
            'is_overdue': bill.is_overdue,
            'created_at': bill.created_at.isoformat() if bill.created_at else None,
        } for bill in bills]


class ResidentCreateUpdateSerializer(serializers.ModelSerializer):
    property_type = serializers.CharField(source='unit_address', allow_null=True, required=False)
    
    class Meta:
        model = AccountUser
        fields = [
            'name',
            'email_address',
            'phone_number',
            'unit_address',
            'property_type',
            'approved_by_admin',
            'profile_image_url',
        ]
    
    def validate_email_address(self, value):
        instance = self.instance
        if instance:
            if AccountUser.objects.exclude(id=instance.id).filter(email_address=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        else:
            if AccountUser.objects.filter(email_address=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value


class ApprovalStatusSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=True)


class ResidentStatsSerializer(serializers.Serializer):
    total_residents = serializers.IntegerField()
    approved_residents = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    total_bills = serializers.IntegerField()
    paid_bills = serializers.IntegerField()
    unpaid_bills = serializers.IntegerField()
    pending_bills = serializers.IntegerField()
    overdue_bills = serializers.IntegerField()
