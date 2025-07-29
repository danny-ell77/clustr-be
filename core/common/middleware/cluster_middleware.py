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
        
        Args:
            request: The request object
            
        Returns:
            None
        """
        # Skip for unauthenticated users or admin paths
        if not request.user.is_authenticated or request.path.startswith('/admin/'):
            return None

        # Get the cluster_id from various sources in order of precedence:
        # 1. Request headers
        # 2. Query parameters
        # 3. JWT token payload (set by JWTAuthenticationMiddleware)
        cluster_id = (
            request.headers.get('X-Cluster-ID') or 
            request.GET.get('cluster_id') or 
            getattr(request, '_cluster_id', None)
        )
        
        # If user is authenticated, set the cluster context
        from accounts.models import AccountUser


        if hasattr(request, 'user') and isinstance(request.user, AccountUser):
            user = request.user
            
            # If cluster_id is provided, validate that the user has access to this cluster
            if cluster_id:
                try:
                    # Check if user has access to this cluster via the clusters M2M field
                    if hasattr(user, 'clusters') and user.clusters.filter(id=cluster_id).exists():
                        request.cluster_context = user.clusters.get(id=cluster_id)
                    # Check if user has access via the cluster ForeignKey (legacy)
                    elif user.cluster and str(user.cluster.id) == cluster_id:
                        request.cluster_context = user.cluster
                    else:
                        # User doesn't have access to this cluster
                        logger.warning(
                            f"User {user.id} attempted to access unauthorized cluster {cluster_id}",
                            extra={
                                'user_id': str(user.id),
                                'cluster_id': cluster_id
                            }
                        )
                        request.cluster_context = None
                except Exception as e:
                    from core.common.error_utils import log_exception

                    # Log the error but don't fail the request
                    log_exception(
                        e,
                        log_level=logging.WARNING,
                        request=request,
                        context={'message': 'Error setting cluster context'}
                    )
                    request.cluster_context = None
            else:
                # No cluster_id provided, use the user's primary cluster
                if hasattr(user, 'primary_cluster') and user.primary_cluster:
                    request.cluster_context = user.primary_cluster
                # Fallback to the cluster ForeignKey (legacy)
                elif user.cluster:
                    request.cluster_context = user.cluster
        
        return None