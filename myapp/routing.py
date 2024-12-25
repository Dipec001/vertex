# # chat/routing.py
from django.urls import re_path, path
from . import consumers
from support import consumers as support_consumers

websocket_urlpatterns = [
    re_path(r'ws/test/', consumers.TestConsumer.as_asgi()),
    path('ws/league/global/', consumers.GlobalLeagueConsumer.as_asgi()),
    path('ws/league/company/', consumers.CompanyLeagueConsumer.as_asgi()),
    path('ws/streak/', consumers.StreakConsumer.as_asgi()),
    path('ws/gem/', consumers.GemConsumer.as_asgi()),
    path('ws/feed/user/<int:user_id>/', consumers.FeedConsumer.as_asgi()),
    path('ws/feed/company/', consumers.FeedConsumer.as_asgi()),
    path('ws/draw/<int:draw_id>/', consumers.DrawConsumer.as_asgi()),
    path('ws/league/global/status/', consumers.CustomGlobalLeagueConsumer.as_asgi()),
    path('ws/league/company/status/', consumers.CustomCompanyLeagueConsumer.as_asgi()),
    # path('ws/transaction/<int:user_id>/', consumers.TransactionConsumer.as_asgi()),
    path('ws/notification/', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/ticket/(?P<ticket_id>\w+)/$', support_consumers.TicketConsumer.as_asgi()),
    path('ws/<path:path>', consumers.InvalidPathConsumer.as_asgi()),
]
