# # chat/routing.py
from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    # re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/test/', consumers.TestConsumer.as_asgi()),
    # re_path(r'ws/league/(?P<league_id>\d+)/$', consumers.LeagueConsumer.as_asgi()),
    path('ws/league/<int:league_id>/', consumers.LeagueConsumer.as_asgi())

]