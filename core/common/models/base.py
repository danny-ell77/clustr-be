"""
Base models for ClustR application.
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.managers import ClusterFilteredManager

class ObjectHistoryTracker(models.Model):
    """Abstract class for keeping track of creation and changes made to a model object"""

    created_at = models.DateTimeField(
        verbose_name=_("creation date"),
        # # editable=False,
        auto_now_add=True,
    )
    created_by = models.UUIDField(
        verbose_name=_("created by"),
        # # editable=False,
        null=True,
        help_text=_("the Id of the ClustR account user who added this object."),
    )
    last_modified_at = models.DateTimeField(
        verbose_name=_("last modified date"),
        # # editable=False,
        auto_now=True,
    )
    last_modified_by = models.UUIDField(
        verbose_name=_("last modified by"),
        null=True,
        # # editable=False,
        help_text=_("the Id of the ClustR account user who last modified this object."),
    )

    class Meta:
        abstract = True


class UUIDPrimaryKey(models.Model):
    id = models.UUIDField(
        verbose_name="id",
        primary_key=True,
        default=uuid.uuid4,
        # # editable=False,
        help_text=_("UUID primary key"),
    )

    class Meta:
        abstract = True


class ObjectOwnerId(models.Model):
    owner_id = models.UUIDField(
        verbose_name=_("owner id"),
        help_text=_("the Id of the BigCommand account owner."),
        # # editable=False,
    )

    class Meta:
        abstract = True


class AbstractClusterModel(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    Base model for all cluster-related models.
    Provides cluster-based filtering for multi-tenant data isolation.
    """

    cluster = models.ForeignKey(
        verbose_name=_("cluster"),
        to="common.Cluster",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        related_query_name="%(class)s",
        help_text=_("The cluster this object belongs to"),
    )

    # Use the cluster-filtered manager
    objects = ClusterFilteredManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Override save to ensure cluster context is set.
        """
        # If cluster is not set, try to get it from the current request
        if not self.cluster_id:
            from threading import local

            thread_local = local()
            request = getattr(thread_local, "request", None)

            if (
                request
                and hasattr(request, "cluster_context")
                and request.cluster_context
            ):
                self.cluster = request.cluster_context

        super().save(*args, **kwargs)
