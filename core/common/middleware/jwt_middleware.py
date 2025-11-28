"""
JWT Authentication Middleware for ClustR application.

This middleware handles JWT authentication and extracts cluster context from tokens:
- Extracting cluster context from tokens
- Preparing requests for authentication by DRF authentication classes
"""

import logging
import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest


# Configure logger
logger = logging.getLogger('clustr')


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to handle JWT authentication and extract cluster context from tokens.
    
    This middleware prepares the request for authentication by DRF authentication classes
    and extracts cluster context from tokens for multi-tenant support.
    """
    
    def process_request(self, request: HttpRequest):
        """
        Process the request and prepare for JWT authentication.
        
        Args:
            request: The request object
            
        Returns:
            None
        """
        if request.path.startswith('/admin/'):
            return None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.split(' ')[1]
            
            try:
                secret_key = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
                algorithms = getattr(settings, 'JWT_ALGORITHMS', ['HS256'])
                
                payload = jwt.decode(
                    jwt_token,
                    secret_key,
                    algorithms=algorithms,
                    options={'verify_signature': False}
                )
                
                request._jwt_payload = payload
                
                user_id = payload.get('user_id')
                if user_id:
                    request._auth_user_id = user_id
                
                self._extract_context(request, payload)
                
            except Exception as e:
                from core.common.error_utils import log_exception

                log_exception(
                    e,
                    log_level=logging.DEBUG,
                    request=request,
                    context={'message': 'Error extracting JWT payload in middleware'}
                )
            
        return None
    
    def _extract_context(self, request: HttpRequest, payload: dict):
        """
        Extract cluster context from the token payload.
        
        Args:
            request: The request object
            payload: The token payload
        """
        cluster_id = payload.get('cluster_id')
        if cluster_id:
            request._cluster_id = cluster_id