from typing import Type

from django.db.models import TextChoices

from accounts.models.roles import PRIMARY_ROLE_NAME


class AccessControlPermissions(TextChoices):
    ViewInvitation = "ViewInvitation"
    ManageInvitation = "ManageInvitation"
    ViewVisitRequest = "ViewVisitRequest"
    ManageVisitRequest = "ManageVisitRequest"
    ViewGuest = "ViewGuest"
    ManageGuest = "ManageGuest"
    ViewEvent = "ViewEvent"
    ManageEvent = "ManageEvent"
    ViewWard = "ViewWard"
    ManageWard = "ManageWard"
    ViewExit = "ViewExit"
    ManageExit = "ManageExit"


class AccountsPermissions(TextChoices):
    ViewAccountUser = "ViewAccountUser"
    ManageAccountUser = "ManageAccountUser"
    ViewResidents = "ViewResidents"
    ManageResidents = "ManageResidents"
    ViewRoles = "ViewRoles"
    ManageRoles = "ManageRoles"


class CommunicationsPermissions(TextChoices):
    ViewEmergency = "ViewEmergency"
    ManageEmergency = "ManageEmergency"
    ViewEmergencyContacts = "ViewEmergencyContacts"
    ManageEmergencyContacts = "ManageEmergencyContacts"
    ViewComplaint = "ViewComplaint"
    ManageComplaint = "ManageComplaint"
    ViewAnnouncement = "ViewAnnouncement"
    ManageAnnouncement = "ManageAnnouncement"
    ViewPoll = "ViewPoll"
    ManagePoll = "ManagePoll"
    ChangePollSettings = "ChangePollSettings"
    ViewOptions = "ViewOptions"
    ManageOptions = "ManageOptions"
    ViewResponses = "ViewResponses"
    ManageResponses = "ManageResponses"


class DocumentationPermissions(TextChoices):
    ViewDocuments = "ViewDocuments"
    ManageDocuments = "ManageDocuments"


class FacilityAdminPermissions(TextChoices):
    ViewWorkShift = "ViewWorkShift"
    ManageWorkShift = "ManageWorkShift"
    ViewWorkTask = "ViewWorkTask"
    ManageWorkTask = "ManageWorkTask"


class MarketplacePermissions(TextChoices):
    ViewSeller = "ViewSeller"
    ManageSeller = "ManageSeller"
    ViewPost = "ViewPost"
    ManagePost = "ManagePost"
    ViewTags = "ViewTags"
    ManageTags = "ManageTags"
    ViewReview = "ViewReview"
    ManageReview = "ManageReview"


class NotificationsPermissions(TextChoices):
    ViewNotification = "ViewNotification"
    ManageNotification = "ManageNotification"
    ReceiveNotifications = "ReceiveNotifications"


class PaymentsPermissions(TextChoices):
    ViewWallet = "ViewWallet"
    ManageWallet = "ManageWallet"
    ViewBill = "ViewBill"
    ManageBill = "ManageBill"
    PayBills = "PayBills"
    ViewTransaction = "ViewTransaction"
    ManageTransaction = "ManageTransaction"


class ServicemenPermissions(TextChoices):
    ViewHandyMen = "ViewHandyMen"
    ManageHandyMen = "ManageHandyMen"


class StaffTrackerPermissions(TextChoices):
    ViewDomesticStaff = "ViewDomesticStaff"
    ManageDomesticStaff = "ManageDomesticStaff"


DEFAULT_PERMISSIONS: list[Type[TextChoices]] = [
    AccessControlPermissions,
    AccountsPermissions,
    CommunicationsPermissions,
    DocumentationPermissions,
    FacilityAdminPermissions,
    MarketplacePermissions,
    NotificationsPermissions,
    PaymentsPermissions,
    ServicemenPermissions,
    StaffTrackerPermissions,
]


class SecurityPermissions(TextChoices):
    """Security-specific permissions"""

    ViewSecurityLog = "ViewSecurityLog"
    ManageSecurityLog = "ManageSecurityLog"
    ViewEmergencyResponse = "ViewEmergencyResponse"
    ManageEmergencyResponse = "ManageEmergencyResponse"
    ViewSecurityAlert = "ViewSecurityAlert"
    ManageSecurityAlert = "ManageSecurityAlert"


class AdminPermissions(TextChoices):
    """Admin-specific permissions"""

    ViewClusterSettings = "ViewClusterSettings"
    ManageClusterSettings = "ManageClusterSettings"
    ViewAuditLog = "ViewAuditLog"
    ManageAuditLog = "ManageAuditLog"
    ViewSystemSettings = "ViewSystemSettings"
    ManageSystemSettings = "ManageSystemSettings"


class ProfilePermissions(TextChoices):
    """Profile-specific permissions"""

    ViewProfile = "ViewProfile"
    ManageProfile = "ManageProfile"
    ViewSettings = "ViewSettings"
    ManageSettings = "ManageSettings"


# Add the new permission types to DEFAULT_PERMISSIONS
DEFAULT_PERMISSIONS: list[Type[TextChoices]] = [
    AccessControlPermissions,
    AccountsPermissions,
    CommunicationsPermissions,
    DocumentationPermissions,
    FacilityAdminPermissions,
    MarketplacePermissions,
    NotificationsPermissions,
    PaymentsPermissions,
    ServicemenPermissions,
    StaffTrackerPermissions,
    SecurityPermissions,
    AdminPermissions,
    ProfilePermissions,
]


DEFAULT_ROLES = {
    PRIMARY_ROLE_NAME: {
        "description": "Has full access to all account features and resources",
        "permissions": [perm for perms in DEFAULT_PERMISSIONS for perm in perms],
    },
    "Security": {
        "description": "Responsible for managing access control and security",
        "permissions": [
            *[perm for perm in AccessControlPermissions],
            *[perm for perm in SecurityPermissions],
            CommunicationsPermissions.ViewEmergency,
            CommunicationsPermissions.ManageEmergency,
            CommunicationsPermissions.ViewEmergencyContacts,
        ],
    },
    "Facility Manager": {
        "description": "Responsible for managing cluster facilities and services",
        "permissions": [
            *[perm for perm in FacilityAdminPermissions],
            *[perm for perm in ServicemenPermissions],
            CommunicationsPermissions.ViewComplaint,
            CommunicationsPermissions.ManageComplaint,
            DocumentationPermissions.ViewDocuments,
        ],
    },
    "Communications Officer": {
        "description": "Responsible for cluster communications and announcements",
        "permissions": [
            *[perm for perm in CommunicationsPermissions],
            *[perm for perm in NotificationsPermissions],
            DocumentationPermissions.ViewDocuments,
        ],
    },
    "Finance Officer": {
        "description": "Responsible for managing payments and billing",
        "permissions": [
            *[perm for perm in PaymentsPermissions],
            DocumentationPermissions.ViewDocuments,
        ],
    },
    "Resident": {
        "description": "Basic resident role with limited permissions",
        "permissions": [
            AccessControlPermissions.ViewInvitation,
            AccessControlPermissions.ManageInvitation,
            AccessControlPermissions.ViewVisitRequest,
            AccessControlPermissions.ManageVisitRequest,
            AccessControlPermissions.ViewGuest,
            AccessControlPermissions.ViewEvent,
            CommunicationsPermissions.ViewAnnouncement,
            CommunicationsPermissions.ViewPoll,
            CommunicationsPermissions.ViewOptions,
            CommunicationsPermissions.ViewResponses,
            CommunicationsPermissions.ViewComplaint,
            CommunicationsPermissions.ManageComplaint,
            DocumentationPermissions.ViewDocuments,
            MarketplacePermissions.ViewPost,
            MarketplacePermissions.ViewSeller,
            MarketplacePermissions.ViewTags,
            MarketplacePermissions.ViewReview,
            NotificationsPermissions.ViewNotification,
            NotificationsPermissions.ReceiveNotifications,
            PaymentsPermissions.ViewWallet,
            PaymentsPermissions.ViewBill,
            PaymentsPermissions.PayBills,
            PaymentsPermissions.ViewTransaction,
            ServicemenPermissions.ViewHandyMen,
            StaffTrackerPermissions.ViewDomesticStaff,
            StaffTrackerPermissions.ManageDomesticStaff,
            *[perm for perm in ProfilePermissions],
        ],
    },
}
