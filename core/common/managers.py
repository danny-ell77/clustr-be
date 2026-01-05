"""
Custom model managers for ClustR application.
"""

from typing import Any, TypeVar

from django.db import models
from django.db.models.query import QuerySet

T = TypeVar('T', bound=models.Model)


class ClusterFilteredManager(models.Manager):
    """
    A manager that filters querysets by cluster for multi-tenant data isolation.
    """
    
    def get_queryset(self) -> QuerySet:
        """
        Return a queryset filtered by the current cluster context if available.
        """
        queryset = super().get_queryset()
        
        # Get the current request from thread local storage
        from django.core.handlers.wsgi import WSGIRequest
        from core.common.middleware.request_middleware import get_current_request
        
        request = get_current_request()
        
        if request and isinstance(request, WSGIRequest) and hasattr(request, 'cluster_context'):
            cluster = request.cluster_context
            if cluster:
                # Filter by cluster if the model has a cluster field
                if hasattr(self.model, 'cluster'):
                    return queryset.filter(cluster=cluster)
        
        return queryset
    
    def for_cluster(self, cluster_id: str) -> QuerySet:
        """
        Return a queryset filtered by the specified cluster.
        
        Args:
            cluster_id: The ID of the cluster to filter by
            
        Returns:
            A queryset filtered by the specified cluster
        """
        queryset = super().get_queryset()
        
        # Filter by cluster if the model has a cluster field
        if hasattr(self.model, 'cluster'):
            return queryset.filter(cluster_id=cluster_id)
        
        return queryset
    
    def create_for_cluster(self, cluster_id: str, **kwargs: Any) -> T:
        """
        Create a new object for the specified cluster.
        
        Args:
            cluster_id: The ID of the cluster to create the object for
            **kwargs: Additional fields to set on the new object
            
        Returns:
            The newly created object
        """
        # Set the cluster field if the model has one
        if hasattr(self.model, 'cluster'):
            kwargs['cluster_id'] = cluster_id
        
        return super().create(**kwargs)