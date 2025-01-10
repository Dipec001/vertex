from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Company, CustomUser
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from vertex import settings
from unittest import skipIf

@skipIf(not settings.DEBUG, "Skip tests in production environment")
class CompanyTests(APITestCase):
    def setUp(self):
        # Create owner
        self.owner = CustomUser.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True,
            is_staff=True,
            is_superuser=True
        )
        
        # Create test image
        self.test_image = SimpleUploadedFile(
            name='test_logo.jpg',
            content=b'',
            content_type='image/jpeg'
        )
        
        # Create company with available fields
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='https://testcompany.com',
            address='123 Test St, Test City, TC 12345',
            email='contact@testcompany.com',
            phone='+1-555-555-5555',
            alternate_phone='+1-555-555-5556',
            logo=self.test_image
        )
        
        # Login as owner
        self.client.force_authenticate(user=self.owner)
        
        # API endpoints
        self.list_url = reverse('company-list')
        self.detail_url = reverse('company-detail', args=[self.company.id])

    def test_create_company(self):
        """Test creating a company with available fields"""
        data = {
            'name': 'New Test Company',
            'domain': 'https://newtestcompany.com',
            'address': '456 New St, New City, NC 67890',
            'email': 'contact@newtestcompany.com',
            'phone': '+1-555-555-5558',
            'alternate_phone': '+1-555-555-5559',
            'owner': self.owner.id
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        created_data = response.json()['data']
        self.assertEqual(created_data['name'], 'New Test Company')
        self.assertEqual(created_data['email'], 'contact@newtestcompany.com')
        self.assertEqual(created_data['phone'], '+1-555-555-5558')

    def test_update_company(self):
        """Test updating company details"""
        data = {
            'phone': '+1-555-555-5559',
            'email': 'updated@testcompany.com',
            'address': 'Updated address'
        }
        
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        updated_data = response.json()['data']
        self.assertEqual(updated_data['phone'], '+1-555-555-5559')
        self.assertEqual(updated_data['email'], 'updated@testcompany.com')
        self.assertEqual(updated_data['address'], 'Updated address')

    def test_company_validation(self):
        """Test company data validation"""
        # Test invalid email
        data = {
            'name': 'Invalid Company',
            'email': 'invalid-email'
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid domain
        data = {
            'name': 'Invalid Company',
            'domain': 'invalid-domain'
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_read_company_details(self):
        """Test reading company details including calculated fields"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()['data']
        # Check all fields from serializer are present
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('owner', data)
        self.assertIn('domain', data)
        self.assertIn('total_employees', data)
        self.assertIn('created_at', data)
        self.assertIn('open_company_support_tickets', data)
        self.assertIn('open_user_support_tickets', data)
        self.assertIn('percentage_of_install', data)
        self.assertIn('active_users', data)
        self.assertIn('email', data)
        self.assertIn('phone', data)
        self.assertIn('alternate_phone', data)
        self.assertIn('address', data)

    def tearDown(self):
        # Clean up uploaded files
        if self.company.logo:
            self.company.logo.delete() 