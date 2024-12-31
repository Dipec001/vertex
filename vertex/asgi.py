"""
ASGI config for vertex project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vertex.settings")

# application = get_asgi_application()


import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from .middleware import TokenAuthMiddleware

# Set the default settings module for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vertex.settings')

from myapp.routing import websocket_urlpatterns
from support.routing import websocket_urlpatterns as support_websocket_urlpatterns

# Initialize the Django ASGI application
# This ensures the AppRegistry is populated and models are available.
django_asgi_app = get_asgi_application()

# Define the application routing
application = ProtocolTypeRouter({
    "http": django_asgi_app,  # Handles HTTP requests
    # You can add other protocols here, like WebSocket, etc.
    # "websocket": (
    #         # AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    #         URLRouter(websocket_urlpatterns)
    #     ),
    "websocket": TokenAuthMiddleware(  # Use the custom JWT middleware here
        AuthMiddlewareStack(  # Stack the Django authentication middleware
            URLRouter(support_websocket_urlpatterns+websocket_urlpatterns)

        )
    ),
})
