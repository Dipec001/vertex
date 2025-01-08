from unittest import skipIf

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from myapp.models import Draw, Prize, Company, Membership
from vertex import settings

User = get_user_model()

@skipIf(not settings.DEBUG, "Skip tests in production environment")
class ManualPrizeViewSetTests(APITestCase):
    def setUp(self):
        # Create company owner
        self.owner = User.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True,
            is_staff=True,  # Make owner an admin
            is_superuser=True
        )

        # Create company
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='test.com'
        )

        # Create employees
        self.employee1 = User.objects.create_user(
            username='emp1@test.com',
            email='emp1@test.com',
            password='testpass123'
        )
        self.employee2 = User.objects.create_user(
            username='emp2@test.com',
            email='emp2@test.com',
            password='testpass123'
        )

        # Create memberships
        Membership.objects.create(user=self.employee1, company=self.company)
        Membership.objects.create(user=self.employee2, company=self.company)
        
        # Set up dates
        self.today = timezone.now().date()
        self.future_date = timezone.now() + timedelta(days=7)
        
        # Create test draws
        self.global_draw = Draw.objects.create(
            draw_name='Test Global Draw',
            draw_type='global',
            draw_date=self.future_date,
            number_of_winners=3,
            is_active=True
        )
        
        self.company_draw = Draw.objects.create(
            draw_name='Test Company Draw',
            draw_type='company',
            company=self.company,
            draw_date=self.future_date,
            number_of_winners=2,
            is_active=True
        )
        
        # Create test prizes
        self.global_prize = Prize.objects.create(
            draw=self.global_draw,
            name='Global Prize',
            description='Test Global Prize',
            value=1000.00,
            quantity=3
        )
        
        self.company_prize = Prize.objects.create(
            draw=self.company_draw,
            name='Company Prize',
            description='Test Company Prize',
            value=500.00,
            quantity=2
        )
        
        # Login as company owner/admin
        self.client.force_authenticate(user=self.owner)
        
        # API endpoints
        self.list_url = reverse('manual-prize-list')
        self.global_prize_detail_url = reverse('manual-prize-detail', args=[self.global_prize.id])
        self.company_prize_detail_url = reverse('manual-prize-detail', args=[self.company_prize.id])

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the endpoints"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_access(self):
        """Test that non-admin employees cannot access the endpoints"""
        self.client.force_authenticate(user=self.employee1)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_prize_list_view(self):
        """Test that the prize list view returns the correct data"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()['data']['results']
        self.assertEqual(len(data), 2)  # Should have both global and company prizes
        self.assertTrue(any(p['name'] == self.global_prize.name for p in data))
        self.assertTrue(any(p['name'] == self.company_prize.name for p in data))

    def test_prize_detail_view(self):
        """Test that the prize detail view returns the correct data"""
        response = self.client.get(self.global_prize_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()['data']
        self.assertEqual(data['name'], self.global_prize.name)
        self.assertEqual(data['value'], '1000.00')
        self.assertEqual(data['quantity'], 3)


    def test_list_prizes(self):
        """Test listing prizes with filters"""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']["results"]), 2)
        
        # Test filtering by draw
        response = self.client.get(f"{self.list_url}?draw={self.global_draw.id}")
        self.assertEqual(len(response.json()['data']["results"]), 1)
        
        # Test value range filtering
        response = self.client.get(f"{self.list_url}?value_min=600&value_max=1000")
        self.assertEqual(len(response.json()['data']['results']), 1)

    def test_update_prize(self):
        """Test updating a prize"""
        data = {
            'name': 'Updated Prize Name',
            'value': 150.00
        }
        
        response = self.client.patch(self.global_prize_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        updated_data = response.json()['data']
        self.assertEqual(updated_data['name'], 'Updated Prize Name')
        self.assertEqual(updated_data['value'], '150.00')
        
        # Verify database update
        self.global_prize.refresh_from_db()
        self.assertEqual(self.global_prize.name, 'Updated Prize Name')
        self.assertEqual(float(self.global_prize.value), 150.00)

    def test_delete_prize(self):
        """Test deleting a prize"""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.delete(self.global_prize_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Prize.objects.count(), 1)

    def test_inactive_draw_prize_creation(self):
        """Test creating prize for inactive draw"""
        self.client.force_authenticate(user=self.owner)
        
        # Make draw inactive
        self.global_draw.is_active = False
        self.global_draw.save()
        
        data = {
            'draw': self.global_draw.id,
            'name': 'New Prize',
            'description': 'New Description',
            'value': 200.00,
            'quantity': 2
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_prize(self):
        """Test creating a prize"""
        data = {
            'draw': self.global_draw.id,
            'name': 'New Prize',
            'description': 'New Description',
            'value': 200.00,
            'quantity': 2
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_data = response.json()['data']
        self.assertEqual(created_data['name'], 'New Prize')
        self.assertEqual(Prize.objects.count(), 3)

    def test_invalid_prize_creation(self):
        """Test validation errors when creating prizes"""
        self.client.force_authenticate(user=self.owner)

        # Test negative value
        data = {
            'draw': self.global_draw.id,
            'name': 'Invalid Prize',
            'description': 'Description',
            'value': -100.00,
            'quantity': 1
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test zero quantity
        data['value'] = 100.00
        data['quantity'] = 0
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def tearDown(self):
        """Clean up after tests"""
        Prize.objects.all().delete()
        Draw.objects.all().delete()
        Membership.objects.all().delete()
        Company.objects.all().delete()
        User.objects.all().delete() 