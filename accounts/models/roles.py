from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext as _g
from django.utils.translation import gettext_lazy as _

from core.common.models import ObjectHistoryTracker

PRIMARY_ROLE_NAME = "Administrator"


class Role(Group, ObjectHistoryTracker):
    """
    Roles are permission groups assigned to staff roles. This is used to determined what data they
    have access to. Its implementation is based on Django's Group class.
    """

    owner = models.ForeignKey(
        verbose_name=_("Primary account"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        limit_choices_to={
            "is_owner": True,
            "is_cluster_admin": True,
            "is_staff": False,
        },
        related_name="roles",
        related_query_name="role",
        # # editable=False,
        help_text="The admin this role belongs to",
    )
    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        default="",
        help_text=_("Description of the role."),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        default_permissions = []

    def __str__(self) -> str:
        return _g(
            "Role: %(role_name)s; Admin: %(full_name)s; Cluster: %(cluster_name)s"
            % {
                "role_name": self.name,
                "full_name": self.owner.name,
                "cluster_name": self.owner.cluster.name if self.owner.cluster else "",
            }
        )

    def save(self, *args, **kwargs):
        self._set_name_from_owner_id()
        super().save(*args, **kwargs)

    def _set_name_from_owner_id(self):
        """
        Include owner's email address prefix to role name for uniqueness. This is because Django's Group name is
        unique for all group objects. We only need name uniqueness per cluster account not globally.
        """
        if not self.name.startswith(str(self.owner.pk)):
            self.name = f"{self.owner.pk}:{self.name}"

    @property
    def display_name(self) -> str:
        """
        Strips out the role primary user's uuid prefix from the role name
        """
        return self.name.removeprefix(f"{self.owner.pk}:")

    def total_subusers(self) -> int:
        return self.user_set.count()

    @property
    def is_owner(self) -> bool:
        print(self.display_name)
        return self.display_name == PRIMARY_ROLE_NAME

    def get_absolute_url(self):
        return reverse(
            "role-detail", kwargs={"pk": str(self.id), "version": settings.API_VERSION}
        )
