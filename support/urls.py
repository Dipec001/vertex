from django.urls import path, include
from . import views

urlpatterns = [
    path('tickets/', views.TicketViewSet.as_view({'get': 'list', 'post': 'create'}), name="ticket-list"),
    path('tickets/stats/', views.TicketViewSet.as_view({'get': 'stats',}), name="ticket-stats"),
    path('tickets/<int:pk>/', views.TicketViewSet.as_view(
        {'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy', 'put': 'update'}), name="ticket-detail"),
    path('tickets/<int:pk>/add_message/', views.TicketViewSet.as_view({'post': 'add_message'}), name="ticket-add-message"),
    path('tickets/<int:pk>/update_status/', views.TicketViewSet.as_view({'patch': 'update_status'}), name="ticket-update-status"),
    path('company/<int:company_id>/tickets/', views.CompanyTicketViewSet.as_view({'post': 'create', 'get': "list"}), name="company-ticket-list"),
    path('company/<int:company_id>/tickets/stats/', views.CompanyTicketViewSet.as_view({'get': "stats"}), name="company-ticket-stats"),
    path('company/<int:company_id>/tickets/<int:pk>/',
         views.CompanyTicketViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'put': 'update', 'get': 'retrieve'}), name="company-ticket-detail"),
]
