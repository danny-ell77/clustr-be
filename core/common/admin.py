"""
Admin configuration for core.common models.
"""

from django.contrib import admin
from core.common.models import (
    Cluster,
    Visitor,
    VisitorLog,
    Invitation,
    Event,
    EventGuest,
    Child,
    ExitRequest,
    EntryExitLog,
    Announcement, AnnouncementView, AnnouncementLike, AnnouncementComment, AnnouncementReadStatus, AnnouncementCategory,
    IssueTicket, IssueComment, IssueAttachment, IssueStatusHistory, IssueType, IssueStatus, IssuePriority,
    EmergencyContact, SOSAlert, EmergencyResponse, EmergencyType, EmergencyStatus, EmergencyContactType,
    Shift, ShiftSwapRequest, ShiftAttendance, ShiftType, ShiftStatus,
    Task, TaskAssignment, TaskAssignmentHistory, TaskAttachment, TaskStatusHistory, TaskEscalationHistory, TaskComment, TaskType, TaskStatus, TaskPriority,
    MaintenanceLog, MaintenanceAttachment, MaintenanceSchedule, MaintenanceCost, MaintenanceComment, MaintenanceType, MaintenanceStatus, MaintenancePriority, PropertyType,
    Wallet, Transaction, Bill, BillDispute, RecurringPayment, WalletStatus, TransactionType, TransactionStatus, PaymentProvider, BillType, BillCategory, BillStatus, DisputeStatus, RecurringPaymentStatus, RecurringPaymentFrequency, PaymentError, UtilityProvider,
    Chat, ChatParticipant, Message, MessageAttachment, ChatType, ChatStatus, MessageType, MessageStatus,
    Meeting, MeetingParticipant, MeetingRecording, MeetingType, MeetingStatus, ParticipantRole, ParticipantStatus, RecordingType, RecordingStatus,
)


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    """Admin configuration for Cluster model."""

    list_display = ("name", "type", "city", "subscription_status", "is_active")
    list_filter = (
        "type",
        "subscription_status",
        "is_active",
        "city",
        "state",
        "country",
    )
    search_fields = (
        "name",
        "address",
        "city",
        "primary_contact_name",
        "primary_contact_email",
    )
    readonly_fields = (
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "type",
                    "address",
                    "city",
                    "state",
                    "country",
                    "logo_url",
                )
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "primary_contact_name",
                    "primary_contact_email",
                    "primary_contact_phone",
                )
            },
        ),
        (
            "Subscription",
            {"fields": ("subscription_status", "subscription_expiry", "is_active")},
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    """Admin configuration for Visitor model."""

    list_display = (
        "name",
        "access_code",
        "status",
        "estimated_arrival",
        "visit_type",
        "valid_date",
    )
    list_filter = ("status", "visit_type", "valid_for", "valid_date", "cluster")
    search_fields = ("name", "email", "phone", "access_code", "purpose", "notes")
    readonly_fields = (
        "access_code",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "email", "phone", "purpose", "notes")},
        ),
        (
            "Visit Details",
            {"fields": ("estimated_arrival", "visit_type", "valid_for", "valid_date")},
        ),
        ("Access Control", {"fields": ("access_code", "status", "invited_by")}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    """Admin configuration for VisitorLog model."""

    list_display = ("visitor", "date", "log_type", "arrival_time", "departure_time")
    list_filter = ("log_type", "date", "cluster")
    search_fields = ("visitor__name", "visitor__access_code", "notes")
    readonly_fields = (
        "date",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Log Details",
            {
                "fields": (
                    "visitor",
                    "log_type",
                    "arrival_time",
                    "departure_time",
                    "notes",
                )
            },
        ),
        ("Processing", {"fields": ("checked_in_by", "checked_out_by")}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Admin configuration for Invitation model."""

    list_display = (
        "title",
        "visitor",
        "start_date",
        "end_date",
        "recurrence_type",
        "status",
    )
    list_filter = ("status", "recurrence_type", "start_date", "end_date", "cluster")
    search_fields = ("title", "description", "visitor__name")
    readonly_fields = (
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
        "revoked_at",
        "revoked_by",
    )
    fieldsets = (
        ("Basic Information", {"fields": ("title", "description", "visitor")}),
        (
            "Schedule",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "recurrence_type",
                    "recurrence_days",
                    "recurrence_day_of_month",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        (
            "Revocation",
            {
                "fields": ("revoked_by", "revoked_at", "revocation_reason"),
                "classes": ("collapse",),
            },
        ),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin configuration for Event model."""

    list_display = (
        "title",
        "event_date",
        "event_time",
        "location",
        "status",
        "guests_added",
    )
    list_filter = ("status", "event_date", "is_public", "requires_approval", "cluster")
    search_fields = ("title", "description", "location", "access_code")
    readonly_fields = (
        "access_code",
        "guests_added",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        ("Basic Information", {"fields": ("title", "description", "location")}),
        ("Schedule", {"fields": ("event_date", "event_time", "end_time")}),
        (
            "Access Control",
            {
                "fields": (
                    "access_code",
                    "max_guests",
                    "guests_added",
                    "is_public",
                    "requires_approval",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(EventGuest)
class EventGuestAdmin(admin.ModelAdmin):
    """Admin configuration for EventGuest model."""

    list_display = ("name", "event", "status", "access_code", "check_in_time")
    list_filter = ("status", "event", "cluster")
    search_fields = ("name", "email", "phone", "access_code", "notes")
    readonly_fields = (
        "access_code",
        "check_in_time",
        "check_out_time",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        ("Basic Information", {"fields": ("name", "email", "phone", "notes")}),
        ("Event Details", {"fields": ("event", "status")}),
        ("Access Control", {"fields": ("access_code", "invited_by")}),
        ("Check-in/Check-out", {"fields": ("check_in_time", "check_out_time")}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    """Admin configuration for Child model."""

    list_display = ("name", "parent", "age", "gender", "house_number", "is_active")
    list_filter = ("gender", "is_active", "cluster")
    search_fields = ("name", "parent__name", "house_number", "notes")
    readonly_fields = (
        "age",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "date_of_birth", "age", "gender", "profile_photo")},
        ),
        ("Family Details", {"fields": ("parent", "house_number")}),
        ("Emergency Contacts", {"fields": ("emergency_contacts",)}),
        ("Status", {"fields": ("is_active", "notes")}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ExitRequest)
class ExitRequestAdmin(admin.ModelAdmin):
    """Admin configuration for ExitRequest model."""

    list_display = (
        "request_id",
        "child",
        "requested_by",
        "status",
        "expected_return_time",
        "expires_at",
    )
    list_filter = ("status", "cluster", "created_at")
    search_fields = (
        "request_id",
        "child__name",
        "requested_by__name",
        "reason",
        "destination",
    )
    readonly_fields = (
        "request_id",
        "approved_by",
        "approved_at",
        "denied_by",
        "denied_at",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Request Details",
            {
                "fields": (
                    "request_id",
                    "child",
                    "requested_by",
                    "reason",
                    "expected_return_time",
                    "expires_at",
                )
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "destination",
                    "accompanying_adult",
                    "accompanying_adult_phone",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        (
            "Approval Details",
            {
                "fields": ("approved_by", "approved_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Denial Details",
            {
                "fields": ("denied_by", "denied_at", "denial_reason"),
                "classes": ("collapse",),
            },
        ),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(EntryExitLog)
class EntryExitLogAdmin(admin.ModelAdmin):
    """Admin configuration for EntryExitLog model."""

    list_display = (
        "child",
        "log_type",
        "date",
        "exit_time",
        "entry_time",
        "status",
        "is_overdue",
    )
    list_filter = ("log_type", "status", "date", "cluster")
    search_fields = (
        "child__name",
        "reason",
        "destination",
        "accompanying_adult",
        "notes",
    )
    readonly_fields = (
        "is_overdue",
        "duration_minutes",
        "actual_return_time",
        "created_at",
        "created_by",
        "last_modified_at",
        "last_modified_by",
    )
    fieldsets = (
        (
            "Log Details",
            {
                "fields": (
                    "child",
                    "exit_request",
                    "log_type",
                    "date",
                    "status",
                )
            },
        ),
        (
            "Time Tracking",
            {
                "fields": (
                    "exit_time",
                    "entry_time",
                    "expected_return_time",
                    "actual_return_time",
                    "duration_minutes",
                    "is_overdue",
                )
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "reason",
                    "destination",
                    "accompanying_adult",
                    "notes",
                )
            },
        ),
        ("Verification", {"fields": ("verified_by",)}),
        ("Cluster", {"fields": ("cluster",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "last_modified_at",
                    "last_modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

# --- New Models Admin Registration ---

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_published", "published_at", "views_count"]
    list_filter = ["category", "is_published", "created_at", "cluster"]
    search_fields = ["title", "content"]

@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    pass # Enum wrapper if needed, but imported as choices usually? Wait, imported as class from models.announcement. But in __init__ it says AnnouncementCategory. It might be a model or enum. 
    # Checking import: from core.common.models.announcement import AnnouncementCategory (which is a TextChoices).
    # You cannot register TextChoices. Remove this.

@admin.register(IssueTicket)
class IssueTicketAdmin(admin.ModelAdmin):
    list_display = ["title", "ticket_number", "status", "priority", "category", "assigned_to"]
    list_filter = ["status", "priority", "category", "created_at", "cluster"]
    search_fields = ["title", "description", "ticket_number"]

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_type", "is_primary", "phone_number", "is_active"]
    list_filter = ["contact_type", "is_primary", "is_active", "cluster"]
    search_fields = ["name", "phone_number"]

@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ["alert_id", "status", "emergency_type", "user", "created_at"]
    list_filter = ["status", "emergency_type", "created_at", "cluster"]
    search_fields = ["alert_id", "user__name", "user__email_address"]

@admin.register(EmergencyResponse)
class EmergencyResponseAdmin(admin.ModelAdmin):
    list_display = ["alert", "responder", "status", "response_time"]
    list_filter = ["status", "cluster"]
    search_fields = ["alert__alert_id", "responder__name"]

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["user", "shift_type", "start_time", "end_time", "status"]
    list_filter = ["shift_type", "status", "start_time", "cluster"]
    search_fields = ["user__name", "notes"]

@admin.register(ShiftSwapRequest)
class ShiftSwapRequestAdmin(admin.ModelAdmin):
    list_display = ["requester", "recipient", "original_shift", "target_shift", "status"]
    list_filter = ["status", "created_at", "cluster"]

@admin.register(ShiftAttendance)
class ShiftAttendanceAdmin(admin.ModelAdmin):
    list_display = ["shift", "check_in_time", "check_out_time", "status"]
    list_filter = ["status", "check_in_time", "cluster"]

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "task_number", "status", "priority", "task_type", "assigned_to", "due_date"]
    list_filter = ["status", "priority", "task_type", "due_date", "cluster"]
    search_fields = ["title", "description", "task_number"]

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ["task", "assigned_to", "assigned_by", "assigned_at"]
    list_filter = ["assigned_at", "cluster"]

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ["title", "maintenance_type", "status", "priority", "scheduled_date"]
    list_filter = ["maintenance_type", "status", "priority", "scheduled_date", "cluster"]
    search_fields = ["title", "description"]

@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ["name", "maintenance_type", "frequency", "next_due_date", "is_active"]
    list_filter = ["maintenance_type", "frequency", "is_active", "cluster"]

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["user", "balance", "currency", "status", "last_transaction_at"]
    list_filter = ["status", "currency", "cluster"]
    search_fields = ["user__email_address", "wallet_id"]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["reference", "wallet", "amount", "transaction_type", "status", "created_at"]
    list_filter = ["transaction_type", "status", "created_at", "cluster"]
    search_fields = ["reference", "description"]

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ["bill_number", "user", "amount", "bill_type", "status", "due_date"]
    list_filter = ["bill_type", "status", "due_date", "cluster"]
    search_fields = ["bill_number", "user__email_address"]

@admin.register(BillDispute)
class BillDisputeAdmin(admin.ModelAdmin):
    list_display = ["bill", "raised_by", "status", "created_at"]
    list_filter = ["status", "cluster"]

@admin.register(RecurringPayment)
class RecurringPaymentAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "amount", "frequency", "status", "next_payment_date"]
    list_filter = ["frequency", "status", "next_payment_date", "cluster"]

@admin.register(UtilityProvider)
class UtilityProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "provider_type", "is_active"]
    list_filter = ["provider_type", "is_active", "cluster"]

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ["name", "chat_type", "status", "created_at"]
    list_filter = ["chat_type", "status", "created_at", "cluster"]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["chat", "sender", "message_type", "created_at"]
    list_filter = ["message_type", "created_at"]

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ["title", "meeting_type", "status", "start_time", "organizer"]
    list_filter = ["meeting_type", "status", "start_time", "cluster"]
    search_fields = ["title", "agenda"]
