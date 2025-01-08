from unittest import skipIf

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from vertex import settings
from myapp.models import Draw, Prize, Company, Membership

User = get_user_model()


@skipIf(not settings.DEBUG, "Skip tests in production environment")
class ManualDrawViewSetTests(APITestCase):
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

        # Login as company owner/admin
        self.client.force_authenticate(user=self.owner)

        # API endpoints
        self.list_url = reverse('manual-draw-list')
        self.global_detail_url = reverse('manual-draw-detail', args=[self.global_draw.id])
        self.company_detail_url = reverse('manual-draw-detail', args=[self.company_draw.id])

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

    def test_draw_list_view(self):
        """Test that the draw list view returns the correct data"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()['data']["results"]
        self.assertEqual(len(data), 5)  # 2+3(triggered by post_Save company)
        self.assertTrue(any(d['draw_name'] == self.global_draw.draw_name for d in data))
        self.assertTrue(any(d['draw_name'] == self.company_draw.draw_name for d in data))


    def test_draw_detail_view(self):
        """Test that the draw detail view returns the correct data"""
        response = self.client.get(self.global_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()['data']
        self.assertEqual(data['draw_name'], self.global_draw.draw_name)
        self.assertEqual(data['draw_type'], 'global')
        self.assertEqual(data['number_of_winners'], 3)


    def test_create_global_draw(self):
        """Test creating a global draw"""
        data = {
            'draw_name': 'New Global Draw',
            'draw_type': 'global',
            'draw_date': (timezone.now() + timedelta(days=30)).isoformat(),
            'number_of_winners': 5
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_data = response.json()['data']
        self.assertEqual(created_data['draw_name'], 'New Global Draw')
        self.assertEqual(Draw.objects.count(), 3+3) # 3+3(triggered by post_Save company)


    def test_create_company_draw(self):
        """Test creating a company draw"""
        data = {
            'draw_name': 'New Company Draw',
            'draw_type': 'company',
            'company': self.company.id,
            'draw_date': (timezone.now() + timedelta(days=30)).isoformat(),
            'number_of_winners': 3
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_data = response.json()['data']
        self.assertEqual(created_data['draw_name'], 'New Company Draw')
        self.assertEqual(created_data['company'], self.company.id)


    def test_update_draw(self):
        """Test updating a draw"""
        data = {
            'draw_name': 'Updated Draw Name',
            'number_of_winners': 5
        }

        response = self.client.patch(self.global_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_data = response.json()['data']
        self.assertEqual(updated_data['draw_name'], 'Updated Draw Name')
        self.assertEqual(updated_data['number_of_winners'], 5)

        # Verify database update
        self.global_draw.refresh_from_db()
        self.assertEqual(self.global_draw.draw_name, 'Updated Draw Name')
        self.assertEqual(self.global_draw.number_of_winners, 5)


    def tearDown(self):
        """Clean up after tests"""
        Draw.objects.all().delete()
        Prize.objects.all().delete()
        Membership.objects.all().delete()
        Company.objects.all().delete()
        User.objects.all().delete()
