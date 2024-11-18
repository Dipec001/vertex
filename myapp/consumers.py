from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or user.is_anonymous:
            await self.close()  # Close the connection if not authenticated
            return
        # Accept the connection
        await self.accept()
        # Send a test message to the client
        await self.send(text_data=json.dumps({"message": "WebSocket connected!"}))

    async def disconnect(self, close_code):
        # Handle disconnection
        print("WebSocket disconnected")

    async def receive(self, text_data):
        # Echo the received message back
        await self.send(text_data=json.dumps({"message": f"You said: {text_data}"}))


# class LeagueConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.league_id = self.scope['url_route']['kwargs']['league_id']
#         print(f"Connecting to league: {self.league_id}")
#         self.group_name = f'league_{self.league_id}'

#         # Add the client to the WebSocket group
#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()
#         print("WebSocket connection accepted.")

#     async def disconnect(self, close_code):
#         # Remove the client from the WebSocket group
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)

#     async def send_league_update(self, event):
#         # Send the ranking update to the WebSocket
#         print(f"Sending data: {event['data']}")
#         await self.send(text_data=json.dumps(event['data']))


class LeagueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the league_id from the URL route
        self.league_id = self.scope['url_route']['kwargs']['league_id']
        print(f"Connecting to league: {self.league_id}")
        self.group_name = f'league_{self.league_id}'

        # Add the client to the WebSocket group for this league
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()
        print("WebSocket connection accepted.")

    async def disconnect(self, close_code):
        # Remove the client from the WebSocket group when disconnected
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_league_update(self, event):
        # Send the ranking update to all users in the league
        print(f"Sending data to all users in league {self.league_id}: {event['data']}")
        await self.send(text_data=json.dumps(event['data']))