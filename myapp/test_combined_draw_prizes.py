from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from myapp.models import CustomUser, Draw, Prize, Company, DrawImage
from datetime import datetime, timedelta
from django.utils.timezone import now


class CombinedDrawPrizeViewSetTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test company
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user,
            domain='https://test.com'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test draw
        self.draw = Draw.objects.create(
            draw_name="Test Draw",
            draw_type="company",
            company=self.company,
            draw_date=now() + timedelta(days=7),
            number_of_winners=3,
            is_active=True
        )

        # Create test prizes
        self.prize1 = Prize.objects.create(
            draw=self.draw,
            name="First Prize",
            description="Top prize",
            value=1000.00,
            quantity=1
        )

        self.prize2 = Prize.objects.create(
            draw=self.draw,
            name="Second Prize",
            description="Runner up prize",
            value=500.00,
            quantity=2
        )

        # Create test draw image
        self.draw_image = DrawImage.objects.create(
            draw=self.draw,
            image_link="https://example.com/image.jpg",
            title="Test Image"
        )

    def test_create_combined_draw_prize(self):
        """Test creating a new combined draw with prizes"""
        url = reverse('combined-draw-prizes-list')
        data = {
            'draw_name': 'New Combined Draw',
            'draw_type': 'company',
            'company': self.company.id,
            'draw_date': (now() + timedelta(days=14)).isoformat(),
            'number_of_winners': 2,
            'is_active': True,
            'prizes': [
                {
                    'name': 'Grand Prize',
                    'description': 'Amazing prize',
                    'value': 2000.00,
                    'quantity': 1
                },
                {
                    'name': 'Runner Up',
                    'description': 'Second best prize',
                    'value': 1000.00,
                    'quantity': 1
                }
            ],
        }
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data, format='json')
        data = response.json()['data']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Draw.objects.count(), 2+3) # The created draw and the 3 draws from the company creation signal
        self.assertEqual(Prize.objects.filter(draw_id=data['id']).count(), 2)

    def test_retrieve_combined_draw_prize(self):
        """Test retrieving a specific combined draw with its prizes and images"""
        url = reverse('combined-draw-prizes-detail', args=[self.draw.id])
        response = self.client.get(url)
        data = response.json()['data']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['draw_name'], 'Test Draw')
        self.assertEqual(len(data['prizes']), 2)

    def test_update_combined_draw_prize(self):
        """Test updating a combined draw with its prizes"""
        url = reverse('combined-draw-prizes-detail', args=[self.draw.id])
        data = {
            'draw_name': 'Updated Draw Name',
            'number_of_winners': 4,
            'prizes': [
                {
                    'id': self.prize1.id,
                    'name': 'Updated Prize',
                    'value': 1500.00,
                    'description': 'Updated description',
                }
            ],
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.draw.refresh_from_db()
        self.assertEqual(self.draw.draw_name, 'Updated Draw Name')
        self.assertEqual(self.draw.number_of_winners, 4)

    def test_delete_combined_draw_prize(self):
        """Test deleting a combined draw with its prizes"""
        url = reverse('combined-draw-prizes-detail', args=[self.draw.id])
        prev_count = Draw.objects.count()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Draw.objects.count(), prev_count - 1)
        self.assertEqual(Prize.objects.count(), 0)
        self.assertEqual(DrawImage.objects.count(), 0)

    def test_validate_draw_date(self):
        """Test validation of draw date being in the future"""
        url = reverse('combined-draw-prizes-list')
        data = {
            'draw_name': 'Invalid Date Draw',
            'draw_type': 'company',
            'company': self.company.id,
            'draw_date': (now() - timedelta(days=1)).isoformat(),
            'number_of_winners': 1,
            'is_active': True,
            'prizes': [
                {
                    'name': 'Prize',
                    'description': 'Test prize',
                    'value': 100.00,
                    'quantity': 1
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('draw_date', str(data['errors']['error']))

    def test_validate_prize_quantity(self):
        """Test validation of prize quantity being positive"""
        url = reverse('combined-draw-prizes-list')
        data = {
            'draw_name': 'Valid Draw',
            'draw_type': 'company',
            'company': self.company.id,
            'draw_date': (now() + timedelta(days=1)).isoformat(),
            'number_of_winners': 1,
            'is_active': True,
            'prizes': [
                {
                    'name': 'Invalid Prize',
                    'description': 'Test prize',
                    'value': 100.00,
                    'quantity': 0  # Invalid quantity
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', data['errors']['error'])

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access the endpoint"""
        self.client.force_authenticate(user=None)
        url = reverse('combined-draw-prizes-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
