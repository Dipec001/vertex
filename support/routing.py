from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    path('ws/ticket/<int:ticket_id>/', consumers.TicketConsumer.as_asgi()),
]
