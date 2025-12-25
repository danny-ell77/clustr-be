from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import refresh_token


class CookieTokenRefreshView(APIView):
    """
    Custom Refresh View that reads the refresh token from the cookie
    and sets the new access token in an HTTP-only cookie.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        refresh_token_str = request.COOKIES.get('refresh_token')
        
        if not refresh_token_str:
            refresh_token_str = request.data.get('refresh')
        
        if not refresh_token_str:
            return Response(
                {'detail': 'Refresh token not provided'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            tokens = refresh_token(refresh_token_str, request)
            
            access_token = tokens.get('access_token')
            new_refresh_token = tokens.get('refresh_token')
            
            response = Response(
                {
                    'detail': 'Token refreshed successfully',
                    'access_token': access_token,
                },
                status=status.HTTP_200_OK
            )
            
            if access_token:
                response.set_cookie(
                    key='access_token',
                    value=access_token,
                    max_age=60 * 15,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                )
            
            if new_refresh_token:
                response.set_cookie(
                    key='refresh_token',
                    value=new_refresh_token,
                    max_age=60 * 60 * 24 * 7,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                )
            
            return response
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
