import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from support.models import Ticket, TicketMessage
from myapp.models import Company
from support.consumers import TicketConsumer
from channels.db import database_sync_to_async
from django.urls import re_path
from channels.routing import URLRouter

@pytest.mark.django_db
@pytest.mark.asyncio
class TestTicketConsumer:
    async def test_connect_and_send_message(self, ticket_setup):
        user, company, ticket = await ticket_setup
        application = URLRouter([
            re_path(r"ws/ticket/(?P<ticket_id>\w+)/$", TicketConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/ws/ticket/{ticket.id}/"
        )
        communicator.scope["user"] = user

        connected, _ = await communicator.connect()
        assert connected

        test_message = "Test message content"
        await communicator.send_json_to({"message": test_message})

        response = await communicator.receive_json_from()
        assert response["message"] == test_message
        assert response["sender_name"] == user.username

        # Get and verify ticket message
        ticket_message = await self.get_ticket_message(ticket, test_message)
        assert ticket_message is not None

        # Compare sender IDs instead of instances
        assert await database_sync_to_async(lambda: ticket_message.sender.id)() == user.id

        await communicator.disconnect()

    @staticmethod
    async def get_ticket_message(ticket, message):
        @database_sync_to_async
        def get_message():
            return TicketMessage.objects.select_related('sender').filter(
                ticket=ticket,
                message=message
            ).first()
        return await get_message()

    async def test_unauthorized_access(self, ticket_setup):
        user, _, ticket = await ticket_setup
        other_user = await self.create_user_with_company("otheruser1")

        application = URLRouter([
            re_path(r"ws/ticket/(?P<ticket_id>\w+)/$", TicketConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/ws/ticket/{ticket.id}/"
        )
        communicator.scope["user"] = other_user

        connected, _ = await communicator.connect()
        assert not connected

    async def test_multiple_clients(self, ticket_setup):
        user, company, ticket = await ticket_setup
        application = URLRouter([
            re_path(r"ws/ticket/(?P<ticket_id>\w+)/$", TicketConsumer.as_asgi()),
        ])

        communicator1 = WebsocketCommunicator(
            application=application,
            path=f"/ws/ticket/{ticket.id}/"
        )
        communicator2 = WebsocketCommunicator(
            application=application,
            path=f"/ws/ticket/{ticket.id}/"
        )

        communicator1.scope["user"] = user
        communicator2.scope["user"] = user

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        assert connected1 and connected2

        test_message = "Message from client 1"
        await communicator1.send_json_to({"message": test_message})

        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        assert response1 == response2
        assert response1["message"] == test_message
        assert response1["sender_name"] == user.username

        await communicator1.disconnect()
        await communicator2.disconnect()

    @staticmethod
    async def create_user_with_company(username):
        @database_sync_to_async
        def create():
            User = get_user_model()
            user = User.objects.create_user(
                username=username,
                email=f"{username}@example.com",
                password="testpass123"
            )
            company = Company.objects.create(
                name=f"{username}'s Company",
                domain=f"{username}.com",
                owner=user
            )
            user.company = company
            user.save()
            return user

        return await create()

@pytest.fixture
async def ticket_setup():
    @database_sync_to_async
    def setup():
        User = get_user_model()
        # TODO: a better way to setup
        from numpy.random import randint
        user = User.objects.create_user(
            username=f'testuser {randint(1,1000)}',
            email=f'test{randint(1,1000)}@example.com',
            password='testpass123'
        )

        company = Company.objects.create(
            name="Test Company",
            domain="test.com",
            owner=user
        )

        user.company = company
        user.save()

        ticket = Ticket.objects.create(
            title="Test Ticket",
            description="Test Description",
            company=company,
            created_by=user
        )

        return user, company, ticket

    return await setup()

@pytest.fixture(autouse=True)
async def clean_db():
    yield

    @database_sync_to_async
    def cleanup():
        TicketMessage.objects.all().delete()
        Ticket.objects.all().delete()
        Company.objects.all().delete()
        get_user_model().objects.all().delete()

    await cleanup()
