from django.test import TestCase
# from rest_framework.exceptions import ValidationError
from .serializers import CompanyOwnerSignupSerializer, InvitationSerializer, NormalUserSignupSerializer, DailyStepsSerializer, WorkoutActivitySerializer, XpSerializer,StreakSerializer
from django.contrib.auth import get_user_model
from .models import Company, Membership, Invitation, WorkoutActivity, Xp, Streak
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from rest_framework.serializers import ValidationError
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError
from django.utils import timezone


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


# class DailyStepsSerializerTest(APITestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create(email='dailystepuser@example.com', password='password123', username='dailystepuser')
#         # self.client.force_authenticate(user=self.user)
#         # Create a request factory instance
#         self.factory = APIRequestFactory()

#         # Mock request object with authenticated user
#         self.request = self.factory.get('/')  # Simulate a GET request (you can use POST if needed)
#         self.request.user = self.user  # Assign the user to the request

#     def test_step_count_validation(self):
#         data = {'step_count': -100}
#         serializer = DailyStepsSerializer(data=data, context={'request': self.request})
#         with self.assertRaises(ValidationError):
#             serializer.is_valid(raise_exception=True)
    
#     def test_future_date_validation(self):
#         future_date = timezone.now().date() + timezone.timedelta(days=1)
#         data = {'step_count': 1000, 'date': future_date}
#         print(f"Test Log: Future Date Passed to Serializer: {data['date']}")
        
#         serializer = DailyStepsSerializer(data=data, context={'request': self.request})
        
#         is_valid = serializer.is_valid()
#         print(f"Test Log: Serializer is_valid() returned: {is_valid}")
#         print(f"Test Log: Serializer Errors: {serializer.errors}")
        
#         if not is_valid:
#             print(f"Test Log: Validation error was raised.")
        
#         # Check if the validation error was properly raised for the 'date' field
#         self.assertIn('date', serializer.errors, "ValidationError for future date was not raised.")


#     def test_create_daily_steps(self):
#         data = {'step_count': 1000}
#         serializer = DailyStepsSerializer(data=data, context={'request': self.request})
#         self.assertTrue(serializer.is_valid())
#         daily_steps = serializer.save()
#         self.assertEqual(daily_steps.user, self.user)
#         self.assertEqual(daily_steps.step_count, 1000)
#         self.assertEqual(daily_steps.xp, 100.0)


# class WorkoutActivitySerializerTest(APITestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create(username="testuser")
#         self.client.force_authenticate(user=self.user)

#     def test_conflicting_workout_times(self):
#         WorkoutActivity.objects.create(
#             user=self.user, start_datetime=timezone.now(), end_datetime=timezone.now() + timezone.timedelta(minutes=30)
#         )
#         data = {
#             'start_datetime': timezone.now(),
#             'end_datetime': timezone.now() + timezone.timedelta(minutes=30),
#             'duration': 30,
#             'activity_type': 'movement'
#         }
#         serializer = WorkoutActivitySerializer(data=data, context={'request': self.client.request()})
#         with self.assertRaises(ValidationError):
#             serializer.is_valid(raise_exception=True)

#     def test_xp_calculation(self):
#         data = {
#             'duration': 60,
#             'activity_type': 'movement',
#             'average_heart_rate': 130,
#             'start_datetime': timezone.now(),
#             'end_datetime': timezone.now() + timezone.timedelta(minutes=60),
#         }
#         serializer = WorkoutActivitySerializer(data=data, context={'request': self.client.request()})
#         self.assertTrue(serializer.is_valid())
#         workout_activity = serializer.save()
#         self.assertEqual(workout_activity.xp, 240)  # Example calculation logic: 200 (duration) + 40 (heart rate)

#     def test_create_workout_activity(self):
#         data = {
#             'duration': 45,
#             'activity_type': 'movement',
#             'average_heart_rate': 120,
#             'start_datetime': timezone.now(),
#             'end_datetime': timezone.now() + timezone.timedelta(minutes=45),
#         }
#         serializer = WorkoutActivitySerializer(data=data, context={'request': self.client.request()})
#         self.assertTrue(serializer.is_valid())
#         workout_activity = serializer.save()
#         self.assertEqual(workout_activity.user, self.user)
#         self.assertEqual(workout_activity.duration, 45)
#         self.assertEqual(workout_activity.xp, 190)  # Example XP calculation



# class XpSerializerTest(APITestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create(username="testuser")
#         self.xp = Xp.objects.create(
#             user=self.user,
#             totalXpToday=200,
#             totalXpAllTime=5000,
#             currentXpRemaining=500
#         )

#     def test_xp_serialization(self):
#         serializer = XpSerializer(self.xp)
#         data = serializer.data
#         self.assertEqual(data['totalXpToday'], 200)
#         self.assertEqual(data['totalXpAllTime'], 5000)

#     def test_xp_deserialization(self):
#         data = {
#             'user': self.user.id,
#             'totalXpToday': 300,
#             'totalXpAllTime': 5300,
#             'currentXpRemaining': 600
#         }
#         serializer = XpSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         xp = serializer.save()
#         self.assertEqual(xp.totalXpToday, 300)
#         self.assertEqual(xp.totalXpAllTime, 5300)


# class StreakSerializerTest(APITestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create(username="testuser")
#         self.streak = Streak.objects.create(
#             user=self.user,
#             current_streak=10,
#             longest_streak=30
#         )

#     def test_streak_serialization(self):
#         serializer = StreakSerializer(self.streak)
#         data = serializer.data
#         self.assertEqual(data['current_streak'], 10)
#         self.assertEqual(data['longest_streak'], 30)

#     def test_streak_deserialization(self):
#         data = {
#             'user': self.user.id,
#             'current_streak': 15,
#             'longest_streak': 35
#         }
#         serializer = StreakSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         streak = serializer.save()
#         self.assertEqual(streak.current_streak, 15)
#         self.assertEqual(streak.longest_streak, 35)
