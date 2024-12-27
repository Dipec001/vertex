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
            company=self.company,
            created_by=self.user
        )
        self.ticket1 = Ticket.objects.create(
            title='ticket1',
            description='ticket1 description',
            company=self.company1,
            created_by=self.user1,
        )

        # URLs
        self.tickets_url = reverse('ticket-list')
        self.ticket_detail_url = reverse('ticket-detail', kwargs={'pk': self.ticket.pk})
        self.ticket_message_url = reverse('ticket-add-message', kwargs={'pk': self.ticket.pk})
        self.ticket_status_url = reverse('ticket-update-status', kwargs={'pk': self.ticket.pk})

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
        self.assertEqual(Ticket.objects.count(), 3)
        self.assertEqual(data['company'], self.user.company.pk)
        self.assertEqual(data['title'], 'New Ticket')

    def test_list_tickets(self):
        """Test listing tickets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]["results"]), 2)

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
        self.client.force_authenticate(user=self.user)
        data = {
            'status': 'in_progress'
        }
        response = self.client.patch(self.ticket_status_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], 'in_progress')

    def test_invalid_ticket_status_update(self):
        """Test updating ticket status with invalid status"""
        self.client.force_authenticate(user=self.user)
        data = {
            'status': 'invalid_status'
        }
        response = self.client.patch(self.ticket_status_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
        # Create test ticket
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            company=self.company,
            created_by=self.user
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
        self.ticket1 = Ticket.objects.create(
            title='ticket1',
            description='ticket1 description',
            company=self.company1,
            created_by=self.user1,
        )


        # URLs
        self.company_tickets_url = reverse('company-ticket-list', kwargs={'company_id': self.company.pk})
        self.company_detail_url = reverse('company-ticket-detail', kwargs={'company_id': self.company.pk ,'pk': self.ticket.pk})

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
        self.assertEqual(Ticket.objects.count(), 3)
        self.assertEqual(data['title'], 'New Ticket')
        self.assertEqual(data['company'], self.company.pk)
        created_ticket = Ticket.objects.get(pk=data['id'])
        self.assertEqual(data['company'], created_ticket.company_id)

    def test_list_tickets(self):
        """Test listing tickets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.company_tickets_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]["results"]), 1)

    def test_retrieve_ticket(self):
        """Test retrieving a specific ticket"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.company_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Test Ticket')

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