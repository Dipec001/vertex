import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.room_group_name = f'ticket_{self.ticket_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Check if user has access to this ticket
        if not await self.can_access_ticket():
            await self.close()
            return

        await self.accept()

    async def disconnect(self, code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save message to database
        ticket_message = await self.save_message(message)

        # Serialize the message
        serialized_message = await self.serialize_message(ticket_message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': serialized_message
            }
        )

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def can_access_ticket(self):
        from .models import Ticket, TicketMessage
        try:
            ticket = Ticket.objects.get(id=self.ticket_id)
            return ticket.company == self.scope['user'].company
        except Ticket.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message):
        from .models import Ticket, TicketMessage
        ticket = Ticket.objects.get(id=self.ticket_id)
        return TicketMessage.objects.create(
            ticket=ticket,
            sender=self.scope['user'],
            message=message
        )

    @database_sync_to_async
    def serialize_message(self, ticket_message):
        from .serializers import TicketMessageSerializer
        return TicketMessageSerializer(ticket_message).data
