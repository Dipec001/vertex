
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import SupportTicket, SupportMessage
from .serializers import SupportTicketSerializer, SupportMessageSerializer

class SupportTicketView(APIView):
    """
    Create and list support tickets for the user.
    """
    def get(self, request):
        tickets = SupportTicket.objects.filter(user=request.user)
        serializer = SupportTicketSerializer(tickets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SupportTicketSerializer(data=request.data)
        if serializer.is_valid():
            # Save the ticket with the authenticated user
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def patch(self, request, *args, **kwargs):
        ticket_id = kwargs.get('pk')  # Assuming the URL includes a `pk` parameter
        try:
            ticket = SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user is either the ticket creator or an admin
        if ticket.user != request.user and not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"detail": "You do not have permission to update this ticket."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Only update the `status` field
        status_value = request.data.get('status')
        if status_value not in dict(SupportTicket.STATUS_CHOICES):
            return Response(
                {"detail": "Invalid status value."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = status_value
        ticket.save()
        return Response({"detail": "Status updated successfully."}, status=status.HTTP_200_OK)



class SupportMessageView(APIView):
    """
    Create and list messages for a specific ticket.
    """
    def get(self, request, ticket_id):
        try:
            # Allow ticket owner or staff to access the ticket
            ticket = SupportTicket.objects.get(id=ticket_id)
            if not (ticket.user == request.user or request.user.is_staff or request.user.is_superuser):
                return Response({'error': 'You do not have permission to access this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        except SupportTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        messages = SupportMessage.objects.filter(ticket=ticket)
        serializer = SupportMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, ticket_id):
        try:
            # Allow ticket owner or staff to access the ticket
            ticket = SupportTicket.objects.get(id=ticket_id)
            if not (ticket.user == request.user or request.user.is_staff or request.user.is_superuser):
                return Response({'error': 'You do not have permission to access this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        except SupportTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        data['ticket'] = ticket.id

        serializer = SupportMessageSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
