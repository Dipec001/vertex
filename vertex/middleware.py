from django.http import JsonResponse
import jwt
from django.apps import apps
from django.conf import settings
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


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
                else:
                    raise ValueError("User ID not found in token.")
            except jwt.ExpiredSignatureError:
                await send({"type": "websocket.close"})
                return
            except jwt.DecodeError:
                await send({"type": "websocket.close"})
                return
            except ValueError:
                await send({"type": "websocket.close"})
                return

        # If token is missing or invalid, close the connection
        if not token or 'user' not in scope:
            await send({"type": "websocket.close"})
            return

        await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        # Dynamically fetch the CustomUser model
        CustomUser = apps.get_model('myapp', 'CustomUser')
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            print('no user')
            return AnonymousUser()  # Return an AnonymousUser instead of None
        
