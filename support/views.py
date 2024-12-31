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

class CompanyTicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [rest_framework.DjangoFilterBackend]
    filterset_class = TicketFilterSet

    def get_queryset(self):
        return Ticket.objects.filter(company=self.kwargs["company_id"], is_individual=False).prefetch_related(
            'messages'
        ).select_related('created_by')

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

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [rest_framework.DjangoFilterBackend]
    filterset_class = TicketFilterSet

    def get_queryset(self):
        queryset = Ticket.objects.prefetch_related('messages').select_related('created_by')
        is_individual = self.request.GET.get('is_individual')
        # check if query params contain is_individual key
        if is_individual is not None:
            return queryset.filter(is_individual=is_individual)
        return queryset

    def perform_create(self, serializer):
        # Set the company to the current user company
        serializer.save(
            created_by=self.request.user,
            company=self.request.user.company
        )

    @action(["GET"], detail=False)
    def stats(self, request):
        queryset = self.get_queryset()
        total_tickets = queryset.count()
        open_tickets = queryset.filter(status="open").count()
        closed_tickets = queryset.filter(status="closed").count()
        data = dict(total_tickets=total_tickets, open_tickets=open_tickets, closed_tickets=closed_tickets)
        return Response(data=data)

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        ticket = self.get_object()
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
        new_status = request.data.get('status')

        if new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            return Response({'status': new_status})
        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )
