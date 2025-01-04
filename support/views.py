from django.db.models import Q
from django.db.models.aggregates import Count
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from django_filters import rest_framework

from myapp.models import Company
from .filters import TicketFilterSet
from .models import Ticket
from .serializers import TicketSerializer, TicketMessageSerializer
from typing import Literal
from rest_framework.views import APIView
from myapp.utils import get_date_range
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class MessagePagination(PageNumberPagination):
    page_size = 20  # Number of messages per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class CompanyTicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [rest_framework.DjangoFilterBackend]
    filterset_class = TicketFilterSet

    def get_queryset(self):
        return Ticket.objects.filter(company=self.kwargs["company_id"], is_individual=False).prefetch_related(
            'messages'
        ).select_related('created_by', 'assigned_to', 'company')

    def perform_create(self, serializer):
        company_id = self.kwargs["company_id"]
        company = Company.objects.get(pk=company_id)

        serializer.save(
            created_by=self.request.user,
            company=company
        )

    @action(["GET"], detail=False)
    def stats(self, request, company_id):
        queryset = self.get_queryset()
        total_tickets=queryset.count()
        open_tickets=queryset.filter(status="open").count()
        closed_tickets=queryset.filter(status="closed").count()
        data = dict(total_tickets=total_tickets, open_tickets=open_tickets, closed_tickets=closed_tickets)
        return Response(data=data)
    
class TicketStatsGraphView(APIView):
    def get(self, request):
        interval: Literal["this_week", "this_month", "last_week"] = self.request.query_params.get('interval') or "this_month"
        daily_stats = []
        for single_date in get_date_range(interval):
            # Get all XP or this date
            daily_created_ticket = Ticket.objects.filter(
                created_at__date=single_date
            ).aggregate(
                total_tickets_created=Count('id')
            )['total_tickets_created'] or 0

            daily_stats.append({
                'date': single_date,
                'total_tickets_created': daily_created_ticket
            })
        return Response(daily_stats)

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [rest_framework.DjangoFilterBackend]
    filterset_class = TicketFilterSet

    def get_queryset(self):
        queryset = Ticket.objects.prefetch_related('messages').select_related('created_by', 'assigned_to', 'company')
        # Only include individual tickets for your implementation
        is_individual = self.request.GET.get('is_individual')
        if is_individual is not None:
            return queryset.filter(is_individual=is_individual)
        return queryset

    def perform_create(self, serializer):
        # Customize company assignment for your use case
        serializer.save(
            created_by=self.request.user,
            company=None  # Assuming individual tickets don't belong to companies
        )


    @action(["GET"], detail=False)
    def stats(self, request):
        queryset = self.get_queryset()
        total_tickets = queryset.count()
        open_tickets = queryset.filter(status="active").count()
        closed_tickets = queryset.filter(status="resolved").count()
        data = dict(total_tickets=total_tickets, open_tickets=open_tickets, closed_tickets=closed_tickets)
        return Response(data=data)

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketMessageSerializer(data=request.data)

        # Check if the ticket is resolved
        if ticket.status == 'resolved':  # Adjust 'resolved' to match your actual status value
            return Response(
                {'error': 'Cannot add a message to a resolved ticket.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and save the message
        serializer = TicketMessageSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(
                ticket=ticket,
                sender=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        ticket = self.get_object()
        # Check if the user is an admin or staff
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Only admin/staff can update the status.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Proceed to update the status if valid
        new_status = request.data.get('status')

        if new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            return Response({'status': new_status})
        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=["get"], url_path="messages")
    def get_messages(self, request, pk=None):
        ticket = self.get_object()
        messages = ticket.messages.all().order_by('-created_at')  # Order messages as needed
        paginator = MessagePagination()
        paginated_messages = paginator.paginate_queryset(messages, request)
        
        serializer = TicketMessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)