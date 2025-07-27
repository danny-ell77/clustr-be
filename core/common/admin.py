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