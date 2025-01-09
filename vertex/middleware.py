from django.http import JsonResponse
import jwt
from django.apps import apps
from django.conf import settings
from channels.db import database_sync_to_async
from django.utils.deprecation import MiddlewareMixin
import logging
from rest_framework_simplejwt.tokens import AccessToken
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CustomResponseMiddleware:
    """
    This middleware handles format for success/error responses to enable seamless integration with FE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        excluded_paths = ["/swagger/", "/docs/"]

        if request.path in excluded_paths:
            return response

        # For DRF responses
        if hasattr(response, "data"):
            is_success = response.status_code >= 200 and response.status_code < 300
            data = {
                "success": is_success,
                "data": response.data if is_success else None,
                "errors": response.data if not is_success else None,
                "status": response.status_code,
            }
            return JsonResponse(data, status=response.status_code)
        # For regular Django HTTP Responses
        return response

class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = None
        query_string = scope.get('query_string', b'').decode()  # Decode from bytes to string

        # Now we can check for 'token' in the query string
        if 'token' in query_string:
            token = query_string.split('=')[1]  # Extract token after '='

        if token:
            try:
                # Decode the token and verify it
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('user_id')
                if user_id:
                    scope['user'] = await self.get_user(user_id) 
                    logger.info(f"User authenticated: {scope['user']}")
                else:
                    raise ValueError("User ID not found in token.")
            except (jwt.ExpiredSignatureError, jwt.DecodeError, ValueError):
                await send({"type": "websocket.close"})
                return

        # If token is missing or invalid, close the connection
        if not token or 'user' not in scope:
            await send({"type": "websocket.close"})
            return

        await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        # Dynamically import AnonymousUser and fetch the CustomUser model
        from django.contrib.auth.models import AnonymousUser  # Import here to avoid early import issues
        CustomUser = apps.get_model('myapp', 'CustomUser')
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            logger.info('No user found, returning AnonymousUser')
            return AnonymousUser()  # Return an AnonymousUser instead of None
    


class ErrorLoggerMiddleware(MiddlewareMixin):
    """
    This middleware handles logging of errors to a log file.
    The file gets created if it doesn't exist, and an email is sent to notify the admin of any logged errors.
    Please see `logging.py` for the mail configuration.
    The 'process_exception' function contains a check to ensure there are no error-log duplicates.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("vertex_error")

    def __call__(self, request):
        request._exception_logged = False
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if not getattr(request, "_exception_logged", False):
            self.logger.exception(exception)
            request._exception_logged = True


class InfoLoggerMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("vertex_info")

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 400 or response.status_code >= 500:
            self.log_request_info(request)
            self.logger.info(response)

        return response

    def log_request_info(self, request):
        self.logger.info(f"Request: {request.method} {request.path}")


class AccessTokenMiddleware(MiddlewareMixin):
    def process_request(self, request):
        from myapp.models import ActiveSession
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        if auth_header:
            token = auth_header.split(' ')[1]
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                # Optionally, you can use a custom claim here if added
                # session_id = access_token['session_id']
                if not ActiveSession.objects.filter(user_id=user_id, token=token).exists():
                    return JsonResponse({
                        "success": False,
                        "data": None,
                        "errors": {"detail": "Invalid access token"},
                        "status": 401
                    }, status=401)
            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "data": None,
                    "errors": {"detail": "Invalid token", "error": str(e)},
                    "status": 401
                }, status=401)
