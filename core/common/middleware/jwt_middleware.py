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
        # Skip for admin paths
        if request.path.startswith('/admin/'):
            return None
            
        # JWT authentication will be handled by DRF authentication classes
        # This middleware is mainly for extracting cluster context from tokens
        
        # Extract token from Authorization header if it exists
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.split(' ')[1]
            
            # Try to decode the token to extract cluster context
            try:
                # Use settings.SECRET_KEY as the default key
                secret_key = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
                algorithms = getattr(settings, 'JWT_ALGORITHMS', ['HS256'])
                
                # Decode the token without verification (just to extract payload)
                # The actual verification will be done by the authentication class
                payload = jwt.decode(
                    jwt_token,
                    secret_key,
                    algorithms=algorithms,
                    options={'verify_signature': False}
                )
                
                # Store the payload in the request for later use
                request._jwt_payload = payload
                
                # Extract user ID from payload
                user_id = payload.get('user_id')
                if user_id:
                    request._auth_user_id = user_id
                
                # Extract cluster context from payload
                self._extract_context(request, payload)
                
            except Exception as e:
                # Log the error but don't fail the request
                # The authentication class will handle the error
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
        # Extract cluster context
        cluster_id = payload.get('cluster_id')
        if cluster_id:
            request._cluster_id = cluster_id