from django.urls import path
from . import views

urlpatterns = [
    path('tickets/', views.SupportTicketView.as_view(), name='support_tickets'),
    path('tickets/<int:pk>/', views.SupportTicketView.as_view(), name='support_ticket_detail'),  # For retrieving and updating a specific ticket
    path('tickets/<int:ticket_id>/messages/', views.SupportMessageView.as_view(), name='support_messages'),

]
