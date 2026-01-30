"""
Request middleware with timing.
"""

import logging
import threading
import time
import uuid

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

_thread_local = threading.local()
logger = logging.getLogger('clustr')


def get_current_request():
    """Get current request from thread local."""
    return getattr(_thread_local, 'request', None)

def set_current_request(request):
    """Set current request to thread local."""
    setattr(_thread_local, 'request', request)

def get_current_user_id():
    """Get current user ID."""
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return str(request.user.id)
    return None


def get_current_cluster_id():
    """Get current cluster ID."""
    request = get_current_request()
    if request and hasattr(request, 'cluster_context') and request.cluster_context:
        return str(request.cluster_context.id)
    return None


class RequestMiddleware(MiddlewareMixin):
    """Request timing and logging middleware."""
    
    def process_request(self, request):
        request.id = str(uuid.uuid4())
        request.start_time = time.time()
        _thread_local.request = request
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id
        
        if hasattr(request, 'start_time') and not self._skip_logging(request.path):
            duration = time.time() - request.start_time
            user_id = get_current_user_id()
            
            logger.info(
                f"{request.method} {request.path} {response.status_code} {duration:.3f}s",
                extra={
                    'request_id': request.id,
                    'user_id': user_id,
                    'duration': duration,
                    'status': response.status_code,
                }
            )
            
            if duration > 1.0:
                logger.warning(f"SLOW: {request.method} {request.path} {duration:.3f}s")
        
        if hasattr(_thread_local, 'request'):
            del _thread_local.request
        
        return response
    
    def _skip_logging(self, path):
        """Skip logging for static/media/health."""
        return any(path.startswith(p) for p in ['/static/', '/media/', '/health/', '/favicon.ico'])