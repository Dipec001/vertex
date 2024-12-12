from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.urls import path
from myapp.permissions import IsCompanyOwner
from myapp.models import CustomUser, Company

# Dummy view to test the permission
class DummyView(APIView):
    permission_classes = [IsCompanyOwner]

    def get(self, request, *args, **kwargs):
        return Response({"message": "Success"}, status=status.HTTP_200_OK)

# URL configuration for the dummy view
urlpatterns = [
    path('companies/<int:company_id>/dummy/', DummyView.as_view(), name='dummy-view'),
    path('companies/', DummyView.as_view(), name='dummy-view-2'),
]

class IsCompanyOwnerPermissionTest(APITestCase):
    def setUp(self):
        # Create a company owner
        self.owner = CustomUser.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="password",
            is_company_owner=True,
        )
        self.company = Company.objects.create(
            name="Test Company", 
            domain="http://testcompany.com", 
            owner=self.owner
        )

        # Create a request factory
        self.factory = APIRequestFactory()

    def test_unauthenticated_user(self):
        """Test permission with unauthenticated user"""
        request = self.factory.get('/companies/{}/dummy/'.format(self.company.id))
        request.user = None

        view = DummyView.as_view()
        response = view(request, company_id=self.company.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_company_id(self):
        """Test permission without company_id parameter"""
        request = self.factory.get('/companies/')
        force_authenticate(request,user=self.owner)

        view = DummyView.as_view()
        
        with self.assertRaises(ValueError) as context:
            response = view(request)
        
        self.assertIn("Company ID is required", str(context.exception))

    def test_non_existent_company(self):
        """Test permission with non-existent company ID"""
        request = self.factory.get('/companies/99999/dummy/')
        force_authenticate(request, user=self.owner)

        view = DummyView.as_view()
        response = view(request, company_id=99999)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_not_company_owner(self):
        """Test permission with user who is not the company owner"""
        non_owner = CustomUser.objects.create_user(
            username="non_owner",
            email="non_owner@test.com",
            password="password"
        )
        
        request = self.factory.get('/companies/{}/dummy/'.format(self.company.id))
        force_authenticate(request, user=non_owner)

        view = DummyView.as_view()
        response = view(request, company_id=self.company.id)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_but_no_company_access(self):
        """Test permission with authenticated user but no company access"""
        other_owner = CustomUser.objects.create_user(
            username="other_owner",
            email="other_owner@test.com",
            password="password",
            is_company_owner=True
        )
        other_company = Company.objects.create(
            name="Other Company",
            domain="http://othercompany.com",
            owner=other_owner
        )
        
        request = self.factory.get('/companies/{}/dummy/'.format(self.company.id))
        force_authenticate(request, user=other_owner)

        view = DummyView.as_view()
        response = view(request, company_id=self.company.id)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 