from django.test import TestCase
# from rest_framework.exceptions import ValidationError
from .serializers import CompanyOwnerSignupSerializer, InvitationSerializer, NormalUserSignupSerializer
from django.contrib.auth import get_user_model
from .models import Company, Membership, Invitation
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from rest_framework.serializers import ValidationError

CustomUser = get_user_model()

class CompanyOwnerSignupSerializerTest(TestCase):
    def test_create_company_owner(self):
        data = {
            'email': 'testowner@example.com',
            'password': 'password123',
            'company_name': 'Test Company',
            'domain': 'https://testcompany.com'
        }

        serializer = CompanyOwnerSignupSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user, company = serializer.save()

        self.assertEqual(user.email, data['email'])
        self.assertEqual(user.is_company_owner, True)
        self.assertEqual(company.name, data['company_name'])
        self.assertEqual(company.domain, data['domain'])

    def test_duplicate_email(self):
        # Create a user with the same email
        CustomUser.objects.create_user(email='testowner@example.com', username='user1', password='password123')

        data = {
            'email': 'testowner@example.com',
            'password': 'password123',
            'company_name': 'Test Company',
            'domain': 'https://testcompany.com'
        }

        serializer = CompanyOwnerSignupSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)



class InvitationSerializerTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='inviter@example.com', password='password123', username='inviter')
        self.company = Company.objects.create(name='Test Company', owner=self.user)
        Membership.objects.create(user=self.user, company=self.company, role='owner')

        # Create a request factory instance
        self.factory = APIRequestFactory()

        # Mock request object with authenticated user
        self.request = self.factory.get('/')  # Simulate a GET request (you can use POST if needed)
        self.request.user = self.user  # Assign the user to the request

    @patch('myapp.serializers.send_invitation_email_task.delay_on_commit')
    def test_create_invitation(self, mock_send_invitation_email_task):
        data = {
            'email': 'invitee@example.com',
            'first_name': 'John',
            'last_name': 'Doe'
        }

        serializer = InvitationSerializer(data=data, context={'request': self.request, 'company': self.company})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invitation = serializer.save()

        self.assertEqual(invitation.email, data['email'])
        mock_send_invitation_email_task.assert_called_once()

    # def test_invite_self(self):
    #     data = {
    #         'email': 'inviter@example.com',  # Same email as the inviter
    #         'first_name': 'John',
    #         'last_name': 'Doe',
    #     }

    #     serializer = InvitationSerializer(data=data, context={'request': self.request, 'company': self.company})
    #     with self.assertRaises(Exception) as cm:
    #         serializer.is_valid(raise_exception=True)


    # def test_user_already_in_company(self):
    #     # Create a user that is already in the company
    #     invitee = CustomUser.objects.create_user(email='invitee@example.com', username='invitee', password='password123')
    #     Membership.objects.create(user=invitee, company=self.company, role='member')  # Ensure invitee is part of the company
    #     invitee.company = self.company
    #     invitee.save()

    #     data = {
    #         'email': 'invitee@example.com',
    #         'first_name': 'John',
    #         'last_name': 'Doe'
    #     }

    #     serializer = InvitationSerializer(data=data, context={'request': self.user, 'company': self.company})
    #     with self.assertRaises(ValidationError):
    #         serializer.is_valid(raise_exception=True)


class NormalUserSignupSerializerTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='inviter@example.com', password='password123', username='inviter')
        self.company = Company.objects.create(name='Test Company', owner=self.user)
        self.invitation = Invitation.objects.create(email='invitee@example.com', first_name='John', last_name='Doe', invite_code='123456', company=self.company, invited_by=self.user)

    def test_create_normal_user(self):
        data = {
            'email': 'invitee@example.com',
            'password': 'password123',
            'username': 'invitee',
            'invitation_id': self.invitation.id,
            'login_type': 'email'
        }

        serializer = NormalUserSignupSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, data['email'])
        self.assertEqual(user.username, data['username'])
        self.assertEqual(user.company, self.invitation.company)  # User should be associated with the company from the invitation

    # def test_user_exists(self):
    #     data = {
    #          'email': 'invitee@example.com',
    #         'password': 'password123',
    #         'username': 'invitee',
    #         'invitation_id': self.invitation.id,
    #         'login_type': 'email'
    #     }
    #     serializer = NormalUserSignupSerializer(data=data)
    #     with self.assertRaises(ValidationError):
    #         serializer.is_valid(raise_exception=True)

    # def test_invalid_invitation(self):
    #     data = {
    #         'email': 'invitee@example.com',
    #         'password': 'password123',
    #         'username': 'invitee',
    #         'invitation_id': 999,  # Invalid invitation ID
    #         'login_type': 'email'
    #     }

    #     serializer = NormalUserSignupSerializer(data=data)
    #     with self.assertRaises(ValidationError):
    #         serializer.is_valid(raise_exception=True)