# # chat/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/test/', consumers.TestConsumer.as_asgi()),
    path('ws/league/global/<int:league_id>/', consumers.LeagueConsumer.as_asgi()),
    path('ws/league/company/<int:league_id>/', consumers.LeagueConsumer.as_asgi()),
    path('ws/streak/<int:user_id>/', consumers.StreakConsumer.as_asgi()),
    path('ws/gem/<int:user_id>/', consumers.GemConsumer.as_asgi()),
    path('ws/feed/user/<int:user_id>/', consumers.FeedConsumer.as_asgi()),
    path('ws/feed/company/<int:company_id>/', consumers.FeedConsumer.as_asgi()),
    path('ws/draw/<int:draw_id>/', consumers.DrawConsumer.as_asgi()),
    # path('ws/transaction/<int:user_id>/', consumers.TransactionConsumer.as_asgi()),
    # path('ws/notification/<int:user_id>/', consumers.NotificationConsumer.as_asgi()),
]