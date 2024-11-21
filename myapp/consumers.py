from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
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


class LeagueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.league_id = self.scope['url_route']['kwargs']['league_id']
        self.user = self.scope['user']
        self.group_name = f'league_{self.league_id}'

        # Validate if the league exists and is active
        is_league_active = await database_sync_to_async(self.league_exists_and_active)(self.league_id)
        if not is_league_active:
            # Close the WebSocket connection with a reason
            await self.close(code=4002, reason="The league does not exist or is not active.")
            return

        # Validate the league and user membership
        is_member = await database_sync_to_async(self.user_is_in_league)(self.user, self.league_id)
        if not is_member:
            # Close the WebSocket connection with a reason
            await self.close(code=4001, reason="User is not a member of this league.")
            return

        # Add the client to the WebSocket group for this league
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Remove the client from the WebSocket group when disconnected
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_league_update(self, event):
        # Send the ranking update to all users in the league
        print(f"Sending data to all users in league {self.league_id}: {event['data']}")
        await self.send(text_data=json.dumps(event['data']))

    @staticmethod
    def user_is_in_league(user, league_id):
        from myapp.models import UserLeague
        return UserLeague.objects.filter(user=user, league_instance__id=league_id).exists()

    @staticmethod
    def league_exists_and_active(league_id):
        from myapp.models import LeagueInstance
        return LeagueInstance.objects.filter(id=league_id, is_active=True).exists()



class StreakConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Initialize group_name to None
        self.group_name = None

        # Get the user_id from the URL route
        self.user_id = self.scope['url_route']['kwargs']['user_id']

        # Get the user ID from the WebSocket connection scope
        current_user_id = self.scope['user'].id

        # Check if the user_id in the URL matches the user ID from the WebSocket scope
        if str(self.user_id) != str(current_user_id):
            # If they don't match, close the connection
            await self.close(code=4003, reason="User ID mismatch.")
            return
        
        self.group_name = f'streak_{self.user_id}'
        # self.group_name = f'user_{self.user_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Ensure that the group_name is set before trying to leave the group
        if self.group_name:
            # Leave the group when the WebSocket is disconnected
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_streak_update(self, event):
        await self.send(text_data=json.dumps({
            'streak_count': event['streak_count']
        }))


class GemConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Initialize group_name to None
        self.group_name = None

        # Get the user_id from the URL route
        self.user_id = self.scope['url_route']['kwargs']['user_id']

        # Get the user ID from the WebSocket connection scope
        current_user_id = self.scope['user'].id

        # Check if the user_id in the URL matches the user ID from the WebSocket scope
        if str(self.user_id) != str(current_user_id):
            # If they don't match, close the connection
            await self.close(code=4003, reason="User ID mismatch.")
            return

        self.group_name = f'gem_{self.user_id}'
        # self.group_name = f'user_{self.user_id}'

        # Join the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Ensure that the group_name is set before trying to leave the group
        if self.group_name:
            # Leave the group when the WebSocket is disconnected
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_gem_update(self, event):
        """
        Handle gem updates sent from the server (via the broadcast mechanism).
        """
        gem_count = event['gem_count']  # Extract the gem count from the event
        
        # Send the gem update to the WebSocket client
        await self.send(text_data=json.dumps({
            'gem_count': gem_count  # Send the gem count to the client
        }))



class FeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.user_id = self.scope['url_route']['kwargs'].get('user_id')
        self.company_id = self.scope['url_route']['kwargs'].get('company_id')

        self.groups = []

        # Subscribe to personal feed if applicable
        if self.user_id:
            if self.user_id == self.user.id or await self.is_following(self.user_id):
                self.groups.append(f'feed_user_{self.user_id}')

        # Subscribe to company feed if applicable
        if self.company_id:
            if await self.is_company_member(self.company_id):
                self.groups.append(f'feed_company_{self.company_id}')

        # If the user doesn't belong to any groups, close the connection
        if not self.groups:
            await self.close(code=4003, reason="User not authorized to receive any feeds")
            return

        # Add the user to all relevant groups
        for group in self.groups:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        for group in self.groups:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def send_feed_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_following(self, user_id):
        from myapp.models import UserFollowing
        return UserFollowing.objects.filter(follower=self.user, following_id=user_id).exists()

    @database_sync_to_async
    def is_company_member(self, company_id):
        return self.user.company and self.user.company.id == company_id
    

class DrawConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.draw_id = self.scope['url_route']['kwargs']['draw_id']
        self.group_name = f'draw_{self.draw_id}'

        # Validate draw ID 
        draw_exists = await self.draw_exists(self.draw_id) 
        if not draw_exists: 
            await self.close(code=4004, reason="Invalid draw ID") 
            return

        # Check if the user has entries in the draw
        has_entry = await self.user_has_entry(self.draw_id)
        if not has_entry:
            print('user has no entry')
            await self.close(code=4003, reason="User not entered in this draw")
            return

        # Add this channel to the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Remove this channel from the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_draw_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async 
    def draw_exists(self, draw_id):
        from myapp.models import Draw
        print("Draw exists")
        return Draw.objects.filter(id=draw_id).exists()

    @database_sync_to_async
    def user_has_entry(self, draw_id):
        from  myapp.models import DrawEntry
        print("user has entry")
        return DrawEntry.objects.filter(draw_id=draw_id, user=self.user).exists()