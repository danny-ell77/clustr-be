from typing import Iterable, Type

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, Permission
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.common.code_generator import CodeGenerator
from core.common.models import ObjectHistoryTracker, UUIDPrimaryKey
from core.common.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from core.common.utils import to_sentence_case


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email_address, password, **extra_fields):
        """
        Create and save a user with the given email_address and password.
        """
        email_address = self.normalize_email(email_address)
        user = self.model(email_address=email_address, **extra_fields)
        user.set_password(password or None)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email_address: str, password: str = None, **extra_fields
    ):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_owner", False)
        extra_fields.setdefault("is_staff", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email_address, password, **extra_fields)

    def create_admin(self, email_address, password, **extra_fields):
        extra_fields.setdefault("is_owner", True)
        extra_fields.setdefault("is_cluster_admin", True)
        extra_fields.setdefault("is_cluster_staff", True)
        # Other related logic in the future
        user = self._create_user(email_address, password, **extra_fields)
        self._create_and_assign_roles(user)
        return user

    def _create_and_assign_roles(self, user):
        from accounts.models import PRIMARY_ROLE_NAME, Role

        for name, default_role in DEFAULT_ROLES.items():
            role = Role.objects.create(
                owner=user,
                name=f"{user.pk}:{name}",
                description=default_role["description"],
            )
            permissions = Permission.objects.filter(
                codename__in=[str(perm.value) for perm in default_role["permissions"]]
            )
            role.permissions.set(permissions)
        role = Role.objects.get(
            name=f"{user.pk}:{PRIMARY_ROLE_NAME}",
        )
        user.groups.set([role])

    def create_owner(self, email_address, password, **extra_fields):
        extra_fields.setdefault("is_owner", True)
        # Other related logic in the future
        user = self._create_user(email_address, password, **extra_fields)
        self._assign_permissions(user)
        return user

    def _assign_permissions(self, user):
        from accounts.models import PRIMARY_ROLE_NAME

        permissions = Permission.objects.filter(
            codename__in=[
                str(perm.value)
                for perm in DEFAULT_ROLES[PRIMARY_ROLE_NAME]["permissions"]
            ]
        )
        user.user_permissions.set(permissions)

    def create_subuser(self, owner, email_address, permissions=None, **extra_fields):
        from accounts.utils import generate_strong_password

        extra_fields.setdefault("owner", owner)
        # Other related logic in the future
        password = generate_strong_password()
        user: AccountUser = self._create_user(email_address, password, **extra_fields)
        if permissions:
            user.user_permissions.set(permissions)
        return user

    def create_staff(self, owner, email_address, roles=None, **extra_fields):
        from accounts.utils import generate_strong_password

        extra_fields.setdefault("owner", owner)
        extra_fields.setdefault("is_cluster_staff", True)
        password = generate_strong_password()
        user: AccountUser = self._create_user(email_address, password, **extra_fields)
        if roles:
            user.groups.set(roles)
        return user


def generate_external_id():
    return CodeGenerator.generate_code(include_alpha=True)


class UserType(models.TextChoices):
    PRIMARY = "PRIMARY"
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    SUB_USER = "SUB_USER"


class AccountUser(UUIDPrimaryKey, ObjectHistoryTracker, AbstractUser):
    username = None
    created_at = None
    email = None

    name = models.CharField(verbose_name=_("name of user"), max_length=255)

    phone_number = models.CharField(
        verbose_name=_("phone number"),
        max_length=16,
        validators=[MinLengthValidator(4), RegexValidator("^\+[1-9]\d{1,14}$")],
        # editable=False,
        help_text=_(
            "The phone number for this subscription in E.164 format. "
            "See details: https://www.twilio.com/docs/glossary/what-e164"
        ),
    )

    email_address = models.EmailField(
        verbose_name=_("email address"), max_length=100, unique=True
    )
    unit_address = models.TextField(
        help_text=_("This is the address of the resident in the cluster"), null=True
    )
    external_id = models.CharField(
        help_text=_(
            "This is the external resident id used for verification and display purposes"
        ),
        default=generate_external_id,
        # editable=False,
    )
    owner = models.ForeignKey(
        verbose_name=_("primary account"),
        null=True,
        to="self",
        on_delete=models.CASCADE,
        help_text=_("this is the primary"),
        related_name=_("subusers"),
        related_query_name=_("subuser"),
        limit_choices_to={"is_owner": False},
    )

    
    profile_image_url = models.URLField(
        verbose_name=_("profile image url"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Profile image of the user."),
    )
    
    # Multi-tenant support - users can belong to multiple clusters
    clusters = models.ManyToManyField(
        verbose_name=_("clusters"),
        to="common.Cluster",
        related_name=_("users"),
        related_query_name=_("user"),
        help_text=_("Clusters that this user belongs to"),
    )
    
    primary_cluster = models.ForeignKey(
        verbose_name=_("primary cluster"),
        to="common.Cluster",
        null=True,
        related_name=_("primary_users"),
        related_query_name=_("primary_user"),
        help_text=_("The primary cluster for this user"),
        on_delete=models.SET_NULL,
    )

    # IDEA: This could be a separate entity with info on the cluster's member property
    property_owner = models.BooleanField(
        verbose_name=_("Property owner"),
        default=False,
    )

    # Enhanced user verification fields
    is_verified = models.BooleanField(
        verbose_name=_("Is verified?"),
        help_text=_("Has this user completed email verification flow?"),
        default=False,
    )
    is_phone_verified = models.BooleanField(
        verbose_name=_("Is phone verified?"),
        help_text=_("Has this user completed phone verification flow?"),
        default=False,
    )
    approved_by_admin = models.BooleanField(
        verbose_name=_("Approved by admin?"),
        help_text=_(
            "Has this account been approved by an admin for the specified cluster?"
        ),
        default=False,
    )
    
    # Account security fields
    failed_login_attempts = models.PositiveIntegerField(
        verbose_name=_("Failed login attempts"),
        help_text=_("Number of consecutive failed login attempts"),
        default=0,
    )
    last_failed_login = models.DateTimeField(
        verbose_name=_("Last failed login"),
        help_text=_("Timestamp of the last failed login attempt"),
        null=True,
        blank=True,
    )
    account_locked_until = models.DateTimeField(
        verbose_name=_("Account locked until"),
        help_text=_("Timestamp until which the account is locked due to failed login attempts"),
        null=True,
        blank=True,
    )
    last_login_ip = models.GenericIPAddressField(
        verbose_name=_("Last login IP"),
        help_text=_("IP address of the last successful login"),
        null=True,
        blank=True,
    )
    
    # User role fields
    is_cluster_admin = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    is_cluster_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email_address"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        default_permissions = []
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ("-date_joined",)
        indexes = (
            models.Index(fields=["name"]),
            models.Index(fields=["email_address"]),
            models.Index(fields=["date_joined"]),
        )
        default_permissions = []
        permissions = [
            (str(member.value), to_sentence_case(member.name).lower())
            for perm in DEFAULT_PERMISSIONS
            for member in list(perm)
        ]

    def __str__(self):
        return (
            f"{self.name} @ {self.primary_cluster.name if self.primary_cluster else self.email_address}"
        )

    def has_any_permission(
        self, perm_list: Iterable[str], obj: Type[models.Model] = None
    ):
        return any(self.has_perm(perm, obj) for perm in perm_list)

    def has_all_permissions(
        self, perm_list: Iterable[str], obj: Type[models.Model] = None
    ):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def get_absolute_url(self):
        return reverse(
            "user-detail", kwargs={"pk": str(self.pk), "version": settings.API_VERSION}
        )

    @property
    def user_type(self) -> UserType:
        if self.is_cluster_admin:
            return UserType.ADMIN
        if self.is_cluster_staff:
            return UserType.STAFF
        if self.is_owner:
            return UserType.PRIMARY
        return UserType.SUB_USER

    def get_owner(self):
        if self.is_owner:
            return self
        return self.owner

    def prepare_for_import(self):
        """
        This method prepares the user instance for save, since import uses bulk_create, the
        prerequisites for creating users are evaluated first before the bulk_create is called
        """
        from accounts.utils import generate_strong_password

        self.is_owner = True
        self.email_address = AccountUser.objects.normalize_email(self.email_address)
        self.password = make_password(generate_strong_password())


class PreviousPasswords(UUIDPrimaryKey):
    """
    Stores users previously used password. This is required when changing password to verify that the user
    is not reusing an old password.
    """

    user = models.OneToOneField(
        verbose_name=_("user"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="previous_passwords",
        # editable=False,
    )
    passwords = ArrayField(
        models.CharField(_("password"), max_length=128),
        null=True,
        size=200,
        default=list,
        help_text=_("List of password hash of users old passwords"),
    )
    last_modified_at = models.DateTimeField(
        verbose_name=_("last modified date"),
        # editable=False,
        auto_now=True,
    )

    class Meta:
        default_permissions = []
        verbose_name = _("previous passwords")
        verbose_name_plural = _("previous passwords")
        default_permissions = []

    def __str__(self):
        return "%(full_name)s's previous passwords" % {"full_name": self.user.name}

    def save(self, *args, **kwargs):
        self.passwords = list(set(self.passwords))
        super().save(*args, **kwargs)
    
    def add_password(self, password_hash, max_history=10):
        """
        Add a new password hash to the history.
        
        Args:
            password_hash: The hashed password to add
            max_history: Maximum number of passwords to keep in history
        """
        if not self.passwords:
            self.passwords = []
        
        # Add new password to the beginning of the list
        if password_hash not in self.passwords:
            self.passwords.insert(0, password_hash)
        
        # Keep only the most recent passwords
        self.passwords = self.passwords[:max_history]
        self.save()
    
    def is_password_reused(self, password_hash):
        """
        Check if a password hash has been used before.
        
        Args:
            password_hash: The hashed password to check
            
        Returns:
            True if the password has been used before, False otherwise
        """
        return password_hash in (self.passwords or [])
    
    def get_password_count(self):
        """Get the number of passwords in history."""
        return len(self.passwords or [])
