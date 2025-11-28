"""
Cluster middleware for ClustR application.

This middleware handles cluster context setting for multi-tenant support:
- Sets cluster context based on request headers, query parameters, or JWT tokens
- Validates user access to the requested cluster
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest

# Configure logger
logger = logging.getLogger('clustr')


class ClusterContextMiddleware(MiddlewareMixin):
    """
    Middleware to set the cluster context for the current request.
    
    This middleware works in conjunction with JWTAuthenticationMiddleware to provide
    multi-tenant data isolation. It sets the cluster context based on:
    1. Request headers (X-Cluster-ID)
    2. Query parameters (cluster_id)
    3. JWT token payload (via _cluster_id set by JWTAuthenticationMiddleware)
    
    The middleware validates that the user has access to the requested cluster.
    """

    def process_request(self, request: HttpRequest):
        """
        Process the request and set the cluster context.
        Get the cluster_id from various sources in order of precedence:
        1. Request headers
        2. Query parameters
        3. JWT token payload (set by JWTAuthenticationMiddleware)
        
        Args:
            request: The request object
            
        Returns:
            None
        """
        request.cluster_context = None
        
        if request.path.startswith('/admin/'):
            return None

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        cluster_id = (
            request.headers.get('X-Cluster-ID') or 
            request.GET.get('cluster_id') or 
            getattr(request, '_cluster_id', None)
        )
        
        from accounts.models import AccountUser

        if not isinstance(request.user, AccountUser):
            return None

        user = request.user
        
        if cluster_id:
            try:
                if hasattr(user, 'clusters') and user.clusters.filter(id=cluster_id).exists():
                    request.cluster_context = user.clusters.get(id=cluster_id)
                elif user.primary_cluster and str(user.primary_cluster.id) == cluster_id:
                    request.cluster_context = user.primary_cluster
                else:
                    logger.warning(
                        f"User {user.id} attempted to access unauthorized cluster {cluster_id}",
                        extra={
                            'user_id': str(user.id),
                            'cluster_id': cluster_id
                        }
                    )
            except Exception as e:
                from core.common.error_utils import log_exception_with_context

                log_exception_with_context(
                    e,
                    log_level=logging.WARNING,
                    request=request,
                    context={'message': 'Error setting cluster context'}
                )
        else:
            if user.primary_cluster:
                request.cluster_context = user.primary_cluster
        
        return None