from django.urls import path
from . import views

urlpatterns = [
    path('send-notification/', views.SendNotificationAPIView.as_view(), name='send_notification'),
]