from django.utils.timezone import localtime, make_aware, is_aware

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from myapp.models import Company, CustomUser
from .models import Ticket, TicketMessage

class TicketViewSetTests(APITestCase):
    def setUp(self):
        # Create company owner
        self.owner = CustomUser.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True
        )

        # Create company
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='test.com'
        )
        self.owner.company = self.company
        self.owner.save()

        # Create regular user
        self.user = CustomUser.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='testpass123',
            company=self.company
        )
        self.company1 = Company.objects.create(
            name='Test Company 2',
            owner=self.owner,
            domain='test2.com'
        )
        self.user1 = CustomUser.objects.create_user(
            username='user1@test.com',
            email='user1@test.com',
            password='testpass123',
            company=self.company1
        )

        # Create test ticket
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            # company=self.company,
            created_by=self.user
        )
        self.ticket1 = Ticket.objects.create(
            title='ticket1',
            description='ticket1 description',
            # company=self.company1,
            created_by=self.user1,
        )
        # create open ticket
        for i in range(0, 10):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                # company=self.company,
                created_by=self.user
            )
        for i in range(0, 10):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                # company=self.company,
                created_by=self.user,
                status="closed"
            )
        for i in range(0, 2):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                # company=self.company,
                created_by=self.user,
                is_individual=True,
            )
        # URLs
        self.tickets_url = reverse('ticket-list')
        self.ticket_detail_url = reverse('ticket-detail', kwargs={'pk': self.ticket.pk})
        self.ticket_message_url = reverse('ticket-add-message', kwargs={'pk': self.ticket.pk})
        self.ticket_status_url = reverse('ticket-update-status', kwargs={'pk': self.ticket.pk})

    def test_create_individual_ticket(self):
        """Test creating a new ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Ticket',
            'description': 'New Description',
            # 'is_individual': True,
        }
        response = self.client.post(self.tickets_url, data)
        data = response.json()['data']
        created_ticket = Ticket.objects.get(pk=data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 25)
        # self.assertEqual(data['company'], self.user.company.pk)
        self.assertEqual(data['title'], 'New Ticket')
        # self.assertTrue(data['is_individual'])
        # self.assertTrue(created_ticket.is_individual)
    def test_create_ticket(self):
        """Test creating a new ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Ticket',
            'description': 'New Description'
        }
        response = self.client.post(self.tickets_url, data)
        data = response.json()['data']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 25)
        # self.assertEqual(data['company'], self.user.company.pk)
        self.assertEqual(data['title'], 'New Ticket')

    def test_get_individual_stats(self):
        self.client.force_authenticate(user=self.user)
        company_ticket_stats_url = reverse("ticket-stats")
        response = self.client.get(company_ticket_stats_url, {"is_individual": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        # self.assertEqual(data["total_tickets"], 2)
        # self.assertEqual(data["open_tickets"], 2)
        self.assertEqual(data["closed_tickets"], 0)

    def test_get_stats(self):
        self.client.force_authenticate(user=self.user)
        company_ticket_stats_url = reverse("ticket-stats")
        response = self.client.get(company_ticket_stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["total_tickets"], 24)
        # self.assertEqual(data["open_tickets"], 14)
        self.assertEqual(data["closed_tickets"], 10)

    # def test_list_individual_tickets(self):
    #     """Test listing tickets"""
    #     self.client.force_authenticate(user=self.user)
    #     response = self.client.get(self.tickets_url, {"is_individual": True})
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.json()["data"]["results"]), 2)
    #     # verify that all results are individual ticket
    #     self.assertTrue(all(ticket["is_individual"] for ticket in response.json()["data"]["results"]))

    def test_list_tickets(self):
        """Test listing tickets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]["results"]), 20)

    def test_retrieve_ticket(self):
        """Test retrieving a specific ticket"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.ticket_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Test Ticket')

    def test_update_ticket(self):
        """Test updating a ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Updated Title',
            'description': 'Updated Description'
        }
        response = self.client.put(self.ticket_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Updated Title')

    def test_add_message_to_ticket(self):
        """Test adding a message to a ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'message': 'Test message'
        }
        response = self.client.post(self.ticket_message_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(response.json()['data']['message'], 'Test message')

    def test_update_ticket_status(self):
        """Test updating ticket status"""
        self.user.is_staff = True
        self.client.force_authenticate(user=self.user)
        data = {
            'status': 'resolved'
        }
        response = self.client.patch(self.ticket_status_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], 'resolved')

    def test_invalid_ticket_status_update(self):
        """Test updating ticket status with invalid status"""
        self.client.force_authenticate(user=self.user)
        data = {
            'status': 'invalid_status'
        }
        response = self.client.patch(self.ticket_status_url, data)
        # self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access tickets"""
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # def test_wrong_company_access(self):
    #     """Test that users cannot access tickets from other companies"""
    #     # Create another company and user
    #     other_company = Company.objects.create(
    #         name='Other Company',
    #         domain='other.com',
    #         owner=self.owner,
    #     )
    #     other_user = CustomUser.objects.create_user(
    #         username='other@other.com',
    #         email='other@other.com',
    #         password='testpass123',
    #         company=other_company
    #     )
    #
    #     self.client.force_authenticate(user=other_user)
    #     response = self.client.get(self.ticket_detail_url)
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_message_with_attachment(self):
        """Test adding a message with an attachment to a ticket"""
        self.client.force_authenticate(user=self.user)
        with open('test_file.txt', 'w') as f:
            f.write('test content')

        with open('test_file.txt', 'rb') as attachment:
            data = {
                'message': 'Test message with attachment',
                'attachment': attachment
            }
            response = self.client.post(
                self.ticket_message_url,
                data,
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertTrue(TicketMessage.objects.first().attachment)

    def test_ticket_message_validation(self):
        """Test ticket message validation"""
        self.client.force_authenticate(user=self.user)
        data = {
            'message': ''  # Empty message should not be allowed
        }
        response = self.client.post(self.ticket_message_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def tearDown(self):
        """Clean up any files created during testing"""
        import os
        if os.path.exists('test_file.txt'):
            os.remove('test_file.txt')
class CompanyTicketViewSetTests(APITestCase):
    def setUp(self):
        # Create company owner
        self.owner = CustomUser.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True
        )

        # Create company
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='test.com'
        )
        self.owner.company = self.company
        self.owner.save()

        # Create regular user
        self.user = CustomUser.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='testpass123',
            company=self.company
        )
        self.company1 = Company.objects.create(
            name='Test Company 2',
            owner=self.owner,
            domain='test2.com'
        )
        self.user1 = CustomUser.objects.create_user(
            username='user1@test.com',
            email='user1@test.com',
            password='testpass123',
            company=self.company1
        )
        # Create test ticket
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            company=self.company,
            created_by=self.user,
            assigned_to=self.user1
        )
        # create open ticket
        for i in range(0, 10):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                company=self.company,
                created_by=self.user
            )
        for i in range(0, 10):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                company=self.company,
                created_by=self.user,
                status="closed"
            )

        for i in range(0, 10):
            Ticket.objects.create(
                title=f'Test Ticket {i}',
                description='Test Description',
                company=self.company1,
                created_by=self.user,
                status="closed"
            )

        self.ticket1 = Ticket.objects.create(
            title='ticket1',
            description='ticket1 description',
            company=self.company1,
            created_by=self.user1,
        )


        # URLs
        self.company_tickets_url = reverse('company-ticket-list', kwargs={'company_id': self.company.pk})
        self.company_detail_url = reverse('company-ticket-detail', kwargs={'company_id': self.company.pk ,'pk': self.ticket.pk})

    def test_create_ticket_with_assigned_user(self):
        """Test creating a new ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Ticket',
            'description': 'New Description',
            'assigned_to': self.user1.pk
        }
        response = self.client.post(self.company_tickets_url, data)
        data = response.json()['data']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 33)
        self.assertEqual(data['title'], 'New Ticket')
        # self.assertEqual(data['company'], self.company.pk)
        created_ticket = Ticket.objects.get(pk=data['id'])
        # self.assertEqual(data['company'], created_ticket.company_id)
        # self.assertEqual(data['assigned_to'], self.user1.pk)
        self.assertEqual(created_ticket.assigned_to, self.user1)

    def test_create_ticket(self):
        """Test creating a new ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Ticket',
            'description': 'New Description'
        }
        response = self.client.post(self.company_tickets_url, data)
        data = response.json()['data']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 33)
        self.assertEqual(data['title'], 'New Ticket')
        # self.assertEqual(data['company'], self.company.pk)
        created_ticket = Ticket.objects.get(pk=data['id'])
        # self.assertEqual(data['company'], created_ticket.company_id)
    def test_get_stats(self):
        self.client.force_authenticate(user=self.user)
        company_ticket_stats_url = reverse("company-ticket-stats", kwargs = {"company_id": self.company.pk})
        response = self.client.get(company_ticket_stats_url)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["total_tickets"], 21)
        # self.assertEqual(data["open_tickets"], 11)
        self.assertEqual(data["closed_tickets"], 10)

    def test_list_tickets(self):
        """Test listing tickets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.company_tickets_url)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]["results"]), 20)

    def test_retrieve_ticket(self):
        """Test retrieving a specific ticket"""
        prev_ticket_message = TicketMessage.objects.create(ticket_id=self.ticket.pk, message="Xp not working")
        last_ticket_message = TicketMessage.objects.create(ticket_id=self.ticket.pk, message="Xp not working 2")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.company_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Test Ticket')
        self.assertEqual(response.json()['data']['status'], 'open')
        self.assertEqual(response.json()['data']['created_by'], self.user.pk)
        self.assertEqual(response.json()['data']['company'], self.company.pk)
        self.assertEqual(response.json()['data']['creator_fullname'], f"{self.user.first_name} {self.user.last_name}")
        self.assertEqual(response.json()['data']['creator_email'], self.user.email)
        self.assertEqual(response.json()['data']['assigned_to'], self.user1.pk)
        self.assertEqual(response.json()['data']['assigned_to_name'], self.user1.username)
        self.assertEqual(response.json()['data']['company_name'], self.ticket.company.name)

        # Ensure created_at is timezone-aware
        if not is_aware(last_ticket_message.created_at):
            aware_datetime = make_aware(last_ticket_message.created_at)
        else:
            aware_datetime = last_ticket_message.created_at

        # Convert to local time and truncate microseconds to milliseconds
        expected_last_message_response = (
                localtime(aware_datetime)
                .replace(microsecond=(aware_datetime.microsecond // 1000) * 1000)  # Truncate to milliseconds
                .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        )

        # Compare the values
        self.assertEqual(response.json()['data']['last_response'], expected_last_message_response)
        if not is_aware(prev_ticket_message.created_at):
            aware_datetime = make_aware(prev_ticket_message.created_at)
        else:
            aware_datetime = prev_ticket_message.created_at

            # Convert to local time and truncate microseconds to milliseconds
        not_to_expected_tobe_last_message_response = (
                localtime(aware_datetime)
                .replace(microsecond=(aware_datetime.microsecond // 1000) * 1000)  # Truncate to milliseconds
                .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        )
        self.assertNotEqual(response.json()['data']['last_response'], not_to_expected_tobe_last_message_response)

    def test_update_ticket(self):
        """Test updating a ticket"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Updated Title',
            'description': 'Updated Description'
        }
        response = self.client.put(self.company_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Updated Title')

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access tickets"""
        response = self.client.get(self.company_tickets_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    #
    # def test_wrong_company_access(self):
    #     """Test that users cannot access tickets from other companies"""
    #     # Create another company and user
    #     other_company = Company.objects.create(
    #         name='Other Company',
    #         domain='other.com',
    #         owner=self.owner,
    #     )
    #     other_user = CustomUser.objects.create_user(
    #         username='other@other.com',
    #         email='other@other.com',
    #         password='testpass123',
    #         company=other_company
    #     )
    #
    #     self.client.force_authenticate(user=other_user)
    #     response = self.client.get(self.ticket_detail_url)
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)