import calendar
import random
from unittest import skipIf

from django.test import client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from datetime import timedelta
from myapp.models import (
    CustomUser, Company, Membership, Xp, DailySteps, Feed
)
from myapp.serializers import EmployeeSerializer
from vertex import settings


# TODO: should check why the db connection is automatically closed when accessing the db on the rest of the tests.
# It work when run one by one
@skipIf(not settings.DEBUG, "Skip tests in production environment")
class CompanyDashboardViewTests(APITestCase):
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

        # Create employees
        self.employee1 = CustomUser.objects.create_user(
            username='emp1@test.com',
            email='emp1@test.com',
            password='testpass123'
        )
        self.employee2 = CustomUser.objects.create_user(
            username='emp2@test.com',
            email='emp2@test.com',
            password='testpass123'
        )

        # Create memberships
        Membership.objects.create(user=self.employee1, company=self.company)
        Membership.objects.create(user=self.employee2, company=self.company)

        # Set up dates
        self.today = timezone.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.week_ago = self.today - timedelta(days=7)
        self.two_weeks_ago = self.today - timedelta(days=14)

        # Create XP records across different dates
        # Today's XP
        Xp.objects.create(
            user=self.employee1,
            timeStamp=timezone.now(),
            date=self.today,
            totalXpToday=100
        )
        Xp.objects.create(
            user=self.employee2,
            timeStamp=timezone.now(),
            date=self.today,
            totalXpToday=200
        )

        # Yesterday's XP
        Xp.objects.create(
            user=self.employee1,
            timeStamp=timezone.now() - timedelta(days=1),
            date=self.yesterday,
            totalXpToday=150
        )
        Xp.objects.create(
            user=self.employee2,
            timeStamp=timezone.now() - timedelta(days=1),
            date=self.yesterday,
            totalXpToday=180
        )

        # Week ago XP
        Xp.objects.create(
            user=self.employee1,
            timeStamp=timezone.now() - timedelta(days=7),
            date=self.week_ago,
            totalXpToday=120
        )
        Xp.objects.create(
            user=self.employee2,
            timeStamp=timezone.now() - timedelta(days=7),
            date=self.week_ago,
            totalXpToday=160
        )

        # Create steps records across different dates
        # Today's steps
        DailySteps.objects.create(
            user=self.employee1,
            date=self.today,
            step_count=5000,
            xp=50,
            timestamp=timezone.now()
        )
        DailySteps.objects.create(
            user=self.employee2,
            date=self.today,
            step_count=7000,
            xp=70,
            timestamp=timezone.now()
        )

        # Yesterday's steps
        DailySteps.objects.create(
            user=self.employee1,
            date=self.yesterday,
            step_count=6000,
            xp=60,
            timestamp=timezone.now() - timedelta(days=1)
        )
        DailySteps.objects.create(
            user=self.employee2,
            date=self.yesterday,
            step_count=8000,
            xp=80,
            timestamp=timezone.now() - timedelta(days=1)
        )

        # Week ago steps
        DailySteps.objects.create(
            user=self.employee1,
            date=self.week_ago,
            step_count=4500,
            xp=45,
            timestamp=timezone.now() - timedelta(days=7)
        )
        DailySteps.objects.create(
            user=self.employee2,
            date=self.week_ago,
            step_count=6500,
            xp=65,
            timestamp=timezone.now() - timedelta(days=7)
        )

        # Create feed items across different dates
        # Today's feeds
        Feed.objects.create(
            user=self.employee1,
            feed_type='Milestone',
            content='Reached 10k steps!',
            created_at=timezone.now()
        )
        Feed.objects.create(
            user=self.employee2,
            feed_type='Promotion',
            content='Promoted to Gold League!',
            created_at=timezone.now()
        )

        # Yesterday's feeds
        Feed.objects.create(
            user=self.employee1,
            feed_type='Milestone',
            content='Completed 7 day streak!',
            created_at=timezone.now() - timedelta(days=1)
        )

        # Week ago feeds
        Feed.objects.create(
            user=self.employee2,
            feed_type='Promotion',
            content='Reached Silver League!',
            created_at=timezone.now() - timedelta(days=7)
        )

        # Two weeks ago feeds (should still be visible in 30-day window)
        Feed.objects.create(
            user=self.employee1,
            feed_type='Milestone',
            content='First workout completed!',
            created_at=timezone.now() - timedelta(days=14)
        )

        # Login as company owner
        self.client.force_authenticate(user=self.owner)

        self.url = reverse('company-dashboard')

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the dashboard"""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_owner_access(self):
        """Test that non-company owners cannot access the dashboard"""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dashboard_data_structure(self):
        """Test that the dashboard returns the correct data structure"""
        response = self.client.get(self.url, {"interval": "this_month"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()['data']
        # Check response structure
        self.assertIn('company_stats', data)
        self.assertIn('daily_stats', data)
        self.assertIn('recent_activities', data)

    def test_company_stats_accuracy(self):
        """Test that company statistics are calculated correctly"""
        response = self.client.get(self.url)
        data = response.json()['data']
        company_stats = data['company_stats']

        self.assertEqual(company_stats['total_employees'], 2)
        # Average XP for today only
        self.assertEqual(int(company_stats['avg_xp_per_user']), 157)

    def test_daily_stats_data(self):
        """Test that daily statistics are calculated correctly"""
        response = self.client.get(self.url)
        data = response.json()['data']
        daily_stats = data['daily_stats']

        # Test today's stats
        today_stats = next(
            (stats for stats in daily_stats if stats['date'] == self.today.isoformat()),
            None
        )
        self.assertIsNotNone(today_stats)
        self.assertEqual(today_stats['total_steps'], 12000)  # 5000 + 7000
        self.assertEqual(today_stats['total_xp'], 300)  # 100 + 200

        # Test yesterday's stats
        yesterday_stats = next(
            (stats for stats in daily_stats if stats['date'] == self.yesterday.isoformat()),
            None
        )
        self.assertIsNotNone(yesterday_stats)
        self.assertEqual(yesterday_stats['total_steps'], 14000)  # 6000 + 8000
        self.assertEqual(yesterday_stats['total_xp'], 330)  # 150 + 180

    def test_recent_activities(self):
        """Test that recent activities are returned correctly"""
        response = self.client.get(self.url)
        data = response.json()['data']
        activities = data['recent_activities']

        self.assertEqual(len(activities), 5)  # Total number of feed items created

        # Check most recent activities are first
        self.assertEqual(activities[0]['type'], 'Milestone')  # Today's milestone
        self.assertEqual(activities[1]['type'], 'Promotion')  # Today's promotion

        # Verify content of specific activities
        milestone_contents = [activity['content'] for activity in activities if activity['type'] == 'Milestone']
        self.assertIn('Reached 10k steps!', milestone_contents)
        self.assertIn('Completed 7 day streak!', milestone_contents)
        self.assertIn('First workout completed!', milestone_contents)

    def test_empty_company_data(self):

        """Test dashboard behavior with a company that has no data"""
        new_owner = CustomUser.objects.create_user(
            username='newowner@test.com',
            email='newowner@test.com',
            password='testpass123',
            is_company_owner=True
        )
        new_company = Company.objects.create(
            name='Empty Company',
            owner=new_owner,
            domain='empty.com'
        )
        self.client.force_authenticate(user=new_owner)
        # self.client.login(username='newowner@test.com', password='testpass123')
        response = self.client.get(self.url)
        data = response.json()['data']

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['company_stats']['total_employees'], 0)
        self.assertEqual(data['company_stats']['avg_xp_per_user'], 0)
        (_, last_day) = calendar.monthrange(self.today.year, self.today.month)
        # allways return 30 datas with zeros values
        self.assertEqual(len(data['daily_stats']), last_day)
        self.assertEqual(len(data['recent_activities']), 0)

    def test_date_range_validity(self):
        """Test that the data is properly filtered for the last 30 days"""
        # Create old data that shouldn't appear in results
        old_date = self.today - timedelta(days=31)

        Xp.objects.create(
            user=self.employee1,
            timeStamp=timezone.now() - timedelta(days=31),
            date=old_date,
            totalXpToday=1000
        )

        response = self.client.get(self.url)
        data = response.json()['data']
        daily_stats = data['daily_stats']

        # Check that old data is not included
        old_data = next(
            (stats for stats in daily_stats if stats['date'] == old_date.isoformat()),
            None
        )
        self.assertIsNone(old_data)

    def test_user_downloaded_app(self):
        """Test that the system correctly identifies if a user has downloaded the app."""
        # Assuming self.employee1 is a user who has downloaded the app
        self.employee1.last_login = timezone.now()  # Simulate that the user has logged in
        self.employee1.save()

        # Authenticate as the company owner
        self.client.force_authenticate(user=self.owner)

        # Make a request to the relevant endpoint
        response = self.client.get(self.url)
        data = response.json()
        recent_reactivities = data["data"]["recent_activities"]
        # get the employee 1 from the list of employees in recent activities
        employees = [activity['user'] for activity in recent_reactivities]
        employee1 = [employee for employee in employees if employee["id"]==self.employee1.id][0]

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if the response contains the expected data indicating the app has been downloaded
        self.assertIn('downloaded_the_app', employee1)
        self.assertTrue(employee1['downloaded_the_app'])  # Ensure it returns True

    def test_user_not_downloaded_app(self):
        """Test that the system correctly identifies if a user has not downloaded the app."""
        # Assuming self.employee2 is a user who has not downloaded the app
        # Authenticate as the company owner
        self.client.force_authenticate(user=self.owner)

        # Make a request to the relevant endpoint
        response = self.client.get(self.url)
        data = response.json()
        recent_reactivities = data["data"]["recent_activities"]
        # get the employee 1 from the list of employees in recent activities
        employees = [activity['user'] for activity in recent_reactivities]
        employee1 = [employee for employee in employees if employee["id"] == self.employee1.id][0]

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if the response contains the expected data indicating the app has not been downloaded
        self.assertIn('downloaded_the_app', employee1)
        self.assertFalse(employee1['downloaded_the_app'])  # Ensure it returns False

@skipIf(not settings.DEBUG, "Skip tests in production environment")
class EmployeeByCompanyModelViewTest(APITestCase):
    def setUp(self):
        # Create a company
        self.owner = CustomUser.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="password",
            is_company_owner=True,
        )
        self.company = Company.objects.create(name="Test Company", domain="http://testcompany.com", owner=self.owner)
        self.owner.company = self.company
        self.owner.save()

        # Create a company owner
        Membership.objects.create(user=self.owner, company=self.company, role="owner")

        # Create employees
        self.employee1 = CustomUser.objects.create_user(
            username="employee1",
            email="employee1@test.com",
            password="password",
            company=self.company
        )
        Membership.objects.create(user=self.employee1, company=self.company, role="employee")

        self.employee2 = CustomUser.objects.create_user(
            username="employee2",
            email="employee2@test.com",
            password="password",
            company=self.company
        )
        Membership.objects.create(user=self.employee2, company=self.company, role="employee")

        # Create a user not in the company
        self.other_user = CustomUser.objects.create_user(
            username="other",
            email="other@test.com",
            password="password"
        )

    def test_get_employees_by_company(self):
        # Authenticate as the company owner
        self.client.force_authenticate(user=self.owner)

        # Make a request to the view
        url = reverse('employee-by-company', kwargs={'company_id': self.company.id})
        response = self.client.get(url)

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paginated_data = response.json()["data"]
        # Check the response data
        expected_data = EmployeeSerializer([self.employee1, self.employee2], many=True).data
        self.assertEqual(paginated_data["results"], expected_data)

    def test_filter_employees_by_username(self):
        # Authenticate as the company owner
        self.client.force_authenticate(user=self.owner)

        # Filter by username
        url = reverse('employee-by-company', kwargs={'company_id': self.company.id})
        response = self.client.get(url, {'username': 'employee1'})

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paginated_data = response.json()["data"]
        # Check the response data
        expected_data = EmployeeSerializer([self.employee1], many=True).data
        self.assertEqual(paginated_data["results"], expected_data)

    def test_filter_employees_by_email(self):
        # Authenticate as the company owner
        self.client.force_authenticate(user=self.owner)

        # Filter by email
        url = reverse('employee-by-company', kwargs={'company_id': self.company.id})
        response = self.client.get(url, {'email': 'employee2@test.com'})

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paginated_data = response.json()["data"]
        # Check the response data
        expected_data = EmployeeSerializer([self.employee2], many=True).data
        self.assertEqual(paginated_data["results"], expected_data)

    def test_unauthorized_access(self):
        # Attempt to access the view without authentication
        url = reverse('employee-by-company', kwargs={'company_id': self.company.id})
        response = self.client.get(url)

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_by_non_owner(self):
        # Authenticate as a user not in the company
        self.client.force_authenticate(user=self.other_user)

        # Make a request to the view
        url = reverse('employee-by-company', kwargs={'company_id': self.company.id})
        response = self.client.get(url)

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@skipIf(not settings.DEBUG, "Skip tests in production environment")
class EmployeeDetailsByCompanyModelViewSet(APITestCase):
    def setUp(self) -> None:
        # Create a company
        self.owner = CustomUser.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="password",
            is_company_owner=True,
        )
        self.company = Company.objects.create(name="Test Company", domain="http://testcompany.com", owner=self.owner)
        self.owner.company = self.company
        self.owner.save()

        # Create a company owner
        Membership.objects.create(user=self.owner, company=self.company, role="owner")

        # Create employees
        self.employee1 = CustomUser.objects.create_user(
            username="employee1",
            email="employee1@test.com",
            password="password",
            company=self.company
        )
        Membership.objects.create(user=self.employee1, company=self.company, role="employee")

        self.employee2 = CustomUser.objects.create_user(
            username="employee2",
            email="employee2@test.com",
            password="password",
            company=self.company
        )
        Membership.objects.create(user=self.employee2, company=self.company, role="employee")

        # Create a user not in the company
        self.other_user = CustomUser.objects.create_user(
            username="other",
            email="other@test.com",
            password="password"
        )

    def test_retrieve_employee_by_company_id_and_user_id(self):
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': self.employee1.pk})
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(url)
        data = response.json()["data"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data, EmployeeSerializer(self.employee1).data)

    def test_retrieve_by_unauthenticated_user(self):
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': self.employee1.pk})
        response = self.client.get(url)
        data = response.json()["data"]

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_return_not_found(self):
        NON_EXISTENT_COMPANY_ID = 2
        self.client.force_authenticate(user=self.owner)
        url = reverse('employee-details-by-company', kwargs={'company_id': NON_EXISTENT_COMPANY_ID, 'pk': self.employee1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["errors"]["detail"], 'No Company matches the given query.')

    def test_delete_employee(self):
        """Test that a company owner can delete an employee"""
        self.client.force_authenticate(user=self.owner)
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': self.employee1.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the employee was deleted
        self.assertFalse(CustomUser.objects.filter(pk=self.employee1.pk).exists())
        # Verify the membership was deleted
        self.assertFalse(Membership.objects.filter(user=self.employee1, company=self.company).exists())

    def test_delete_employee_by_unauthorized_user(self):
        """Test that non-owners cannot delete employees"""
        self.client.force_authenticate(user=self.employee2)
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': self.employee1.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Verify the employee was not deleted
        self.assertTrue(CustomUser.objects.filter(pk=self.employee1.pk).exists())
        # Verify the membership was not deleted
        self.assertTrue(Membership.objects.filter(user=self.employee1, company=self.company).exists())

    def test_delete_employee_from_wrong_company(self):
        """Test that an owner cannot delete employees from another company"""
        # Create another company and owner
        other_owner = CustomUser.objects.create_user(
            username="other_owner",
            email="other_owner@test.com",
            password="password",
            is_company_owner=True,
        )
        other_company = Company.objects.create(
            name="Other Company",
            domain="http://othercompany.com",
            owner=other_owner
        )

        self.client.force_authenticate(user=other_owner)
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': self.employee1.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Verify the employee was not deleted
        self.assertTrue(CustomUser.objects.filter(pk=self.employee1.pk).exists())
        # Verify the membership was not deleted
        self.assertTrue(Membership.objects.filter(user=self.employee1, company=self.company).exists())

    def test_delete_non_existent_employee(self):
        NON_EXISTENT_EMPLOYEE_ID = 9999999
        self.client.force_authenticate(user=self.owner)
        url = reverse('employee-details-by-company', kwargs={'company_id': self.company.id, 'pk': NON_EXISTENT_EMPLOYEE_ID})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

@skipIf(not settings.DEBUG, "Skip tests in production environment")
class CompanyViewTests(APITestCase):
    def setUp(self):
        # Create a company owner
        self.owner = CustomUser.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True
        )

        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='test.com'
        )
        self.employee1 = CustomUser.objects.create_user(
                    username='emp1@test.com',
                    email='emp1@test.com',
                    password='testpass123'
                )
        self.employee2 = CustomUser.objects.create_user(
            username='emp2@test.com',
            email='emp2@test.com',
            password='testpass123'
        )

        # Create memberships
        Membership.objects.create(user=self.employee1, company=self.company)
        Membership.objects.create(user=self.employee2, company=self.company)
        self.client.force_authenticate(user=self.owner)

    def test_company_list_view(self):
        """Test that the company list view returns the correct data"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('company-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()['data']['results']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], self.company.name)
        self.assertEqual(data[0]['owner'], self.owner.id)

    def test_company_detail_view(self):
        """Test that the company detail view returns the correct data"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('company-detail', kwargs={'pk': self.company.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()['data']
        self.assertEqual(data['name'], self.company.name)
        self.assertEqual(data['owner'], self.owner.id)  # Assuming owner ID is returned
        # number of employees
        self.assertEqual(data['total_employees'], 2)

    def test_company_detail_view_not_found(self):
        """Test that accessing a non-existent company returns a 404"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('company-detail', kwargs={'pk': 999999}))  # Non-existent ID
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_company(self):
        """Test that a company can be created"""
        new_company_data = {
            'name': 'New Company',
            'domain': 'https://newcompany.com',
            'owner': self.owner.id
        }

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(reverse('company-list'), new_company_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()['data']

        # Verify the company was created
        self.assertEqual(Company.objects.count(), 2)  # One existing + one new
        new_company = Company.objects.get(name='New Company')
        self.assertEqual(new_company.domain, 'https://newcompany.com')
        # Ensure the owner is set correctly
        self.assertEqual(new_company.owner, self.owner)

        self.assertEqual(0, data.get('total_employees'))
        self.assertFalse(Membership.objects.filter(company=new_company).exists())

    def test_create_company_without_owner_ko(self):
        """Test that a company can be created"""
        new_company_data = {
            'name': 'New Company',
            'domain': 'https://newcompany.com',
        }

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(reverse('company-list'), new_company_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_company_with_unexistent_owner_ko(self):
        """Test that a company can be created"""
        new_company_data = {
            'name': 'New Company',
            'domain': 'https://newcompany.com',
            'owner': 999999  # Non-existent ID
        }

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(reverse('company-list'), new_company_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_company(self):
        """Test that a company can be updated"""
        updated_data = {
            'name': 'Updated Company',
            'domain': 'https://updatedcompany.com'
        }

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(reverse('company-detail', kwargs={'pk': self.company.id}), updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]

        # Verify the company was updated
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Updated Company')
        self.assertEqual(self.company.domain, 'https://updatedcompany.com')
        self.assertEqual(data['total_employees'], 2)

    def test_delete_company(self):
        """Test that a company can be deleted"""

        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(reverse('company-detail', kwargs={'pk': self.company.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the company was deleted
        self.assertEqual(Company.objects.count(), 0)

    def test_unauthenticated_access_to_company_list(self):
        """Test that unauthenticated users cannot access the company list"""
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('company-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_access_to_company_detail(self):
        """Test that unauthenticated users cannot access the company detail"""
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('company-detail', kwargs={'pk': self.company.id}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@skipIf(not settings.DEBUG, "Skip tests in production environment")
class TestGlobalStats(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            is_company_owner=True
        )

        self.company = Company.objects.create(
            name='Test Company',
            owner=self.owner,
            domain='test.com'
        )

        self.owner2 = CustomUser.objects.create_user(
            username='owner2@test.com',
            email='owner2@test.com',
            password='testpass123',
            is_company_owner=True
        )

        self.company2 = Company.objects.create(
            name='Test Company 2',
            owner=self.owner2,
            domain='test2.com'
        )

        self.employee5 = CustomUser.objects.create_user(
            username='emp5@test2.com',
            email='emp5@test2.com',
            password='testpass123'
        )
        self.employee6 = CustomUser.objects.create_user(
            username='emp6@test2.com',
            email='emp6@test2.com',
            password='testpass123'
        )

        # Create memberships for second company
        Membership.objects.create(user=self.employee5, company=self.company2)
        Membership.objects.create(user=self.employee6, company=self.company2)


        self.employee3 = CustomUser.objects.create_user(
            username='emp3@test.com',
            email='emp3@test.com',
            password='testpass123'
        )
        self.employee4 = CustomUser.objects.create_user(
            username='emp4@test.com',
            email='emp4@test.com',
            password='testpass123'
        )

        # Create memberships for employees not logged in
        Membership.objects.create(user=self.employee3, company=self.company)
        Membership.objects.create(user=self.employee4, company=self.company)



        # Create employees
        self.employee1 = CustomUser.objects.create_user(
            username='emp1@test.com',
            email='emp1@test.com',
            password='testpass123'
        )
        self.employee2 = CustomUser.objects.create_user(
            username='emp2@test.com',
            email='emp2@test.com',
            password='testpass123'
        )

        # Create memberships
        Membership.objects.create(user=self.employee1, company=self.company)
        Membership.objects.create(user=self.employee2, company=self.company)

        # Login these employees once
        self.employee5.last_login = timezone.now()
        self.employee5.save()

        self.employee6.last_login = timezone.now()
        self.employee6.save()

        self.employee1.last_login = timezone.now()
        self.employee1.save()

        self.employee2.last_login = timezone.now()
        self.employee2.save()
    # test global stats
    def test_global_stats(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('global-stats'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertEqual(data['total_companies'], 2)
        self.assertEqual(data['total_users'], 8)
        self.assertEqual(data['percentage_of_install'], 50.0)

@skipIf(not settings.DEBUG, "Skip tests in production environment")
class TestGlobalXpGraph(APITestCase):
    def setUp(self):
        # Create multiple test users
        self.users = []
        for i in range(5):
            user = CustomUser.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@test.com',
                password='testpass123'
            )
            self.users.append(user)

        # Set up dates
        self.today = timezone.now().date()
        self.dates = {
            'today': self.today,
            'yesterday': self.today - timedelta(days=1),
            'week_ago': self.today - timedelta(days=7),
            'two_weeks_ago': self.today - timedelta(days=14),
            'month_ago': self.today - timedelta(days=29)  # Within 30-day window
        }

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the XP graph data"""
        response = self.client.get(reverse('global-xp-graphs'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access(self):
        """Test that authenticated users can access the XP graph data"""
        self.client.force_authenticate(user=self.users[0])
        response = self.client.get(reverse('global-xp-graphs'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multiple_users_same_day(self):
        """Test XP aggregation when multiple users have records on the same day"""
        # Create one XP record per user for today
        xp_values = [100, 150, 200, 250, 300]
        expected_total = sum(xp_values)

        for user, xp_value in zip(self.users, xp_values):
            Xp.objects.create(
                user=user,
                timeStamp=timezone.now(),
                date=self.dates['today'],
                totalXpToday=xp_value
            )

        self.client.force_authenticate(user=self.users[0])
        response = self.client.get(reverse('global-xp-graphs'))
        data = response.json()['data']

        today_data = next((d for d in data if d['date'] == self.dates['today'].isoformat()), None)
        self.assertEqual(today_data['total_xp'], expected_total)

    def test_scattered_data_across_days(self):
        """Test XP aggregation when users have records scattered across different days"""
        # Create scattered XP records - ensuring one record per user per day
        test_data = [
            (self.users[0], self.dates['today'], 100),
            (self.users[1], self.dates['today'], 150),
            (self.users[2], self.dates['yesterday'], 200),
            (self.users[3], self.dates['yesterday'], 250),
            (self.users[4], self.dates['week_ago'], 300),
            (self.users[0], self.dates['week_ago'], 350),  # Different day for same user is OK
        ]

        for user, date, xp in test_data:
            Xp.objects.create(
                user=user,
                timeStamp=timezone.now(),
                date=date,
                totalXpToday=xp
            )

        self.client.force_authenticate(user=self.users[0])
        response = self.client.get(reverse('global-xp-graphs'))
        data = response.json()['data']

        # Verify aggregated XP for each day
        expected_totals = {
            self.dates['today'].isoformat(): 250,  # 100 + 150
            self.dates['yesterday'].isoformat(): 450,  # 200 + 250
            self.dates['week_ago'].isoformat(): 650,  # 300 + 350
        }

        for day_data in data:
            if day_data['date'] in expected_totals:
                self.assertEqual(day_data['total_xp'], expected_totals[day_data['date']])

    def test_data_distribution_over_x_days(self):
        """Test XP distribution over the full x-day period"""
        # Create XP records distributed over x days
        (_, last_day) = calendar.monthrange(self.today.year, self.today.month)
        all_dates = [self.today - timedelta(days=x) for x in range(last_day)]
        expected_totals = {}

        # For each date, assign XP to different users
        for date in all_dates:
            daily_xp = 0
            # Rotate through users for each date to avoid duplicate (user, date) combinations
            users_for_this_date = self.users[:3]  # Use first 3 users
            for user in users_for_this_date:
                xp_value = random.randint(50, 200)
                daily_xp += xp_value
                Xp.objects.create(
                    user=user,
                    timeStamp=timezone.now(),
                    date=date,
                    totalXpToday=xp_value
                )
            expected_totals[date.isoformat()] = daily_xp

        self.client.force_authenticate(user=self.users[0])
        response = self.client.get(reverse('global-xp-graphs'))
        data = response.json()['data']
        # Verify we have data for all data for each day of the month
        self.assertEqual(len(data), last_day)

    def test_edge_case_data(self):
        """Test edge cases in XP data"""
        # Create one record per user with edge case values
        test_data = [
            (self.users[0], 0),          # Zero XP
            (self.users[1], 999999),     # Very large XP
            (self.users[2], 0.1),        # Minimal XP
        ]

        expected_total = sum(xp for _, xp in test_data)

        for user, xp_value in test_data:
            Xp.objects.create(
                user=user,
                timeStamp=timezone.now(),
                date=self.dates['today'],
                totalXpToday=xp_value
            )

        self.client.force_authenticate(user=self.users[0])
        response = self.client.get(reverse('global-xp-graphs'))
        data = response.json()['data']

        today_data = next((d for d in data if d['date'] == self.dates['today'].isoformat()), None)
        self.assertEqual(today_data['total_xp'], expected_total)

    def test_data_consistency_over_multiple_requests(self):
        """Test that data remains consistent over multiple requests"""
        # Create one XP record per user
        for i, user in enumerate(self.users):
            Xp.objects.create(
                user=user,
                timeStamp=timezone.now(),
                date=self.dates['today'],
                totalXpToday=100 * (i + 1)  # Different values for each user
            )

        self.client.force_authenticate(user=self.users[0])

        # Make multiple requests and verify consistency
        responses = []
        for _ in range(5):
            response = self.client.get(reverse('global-xp-graphs'))
            responses.append(response.json()['data'])

        # Verify all responses are identical
        first_response = responses[0]
        for response in responses[1:]:
            self.assertEqual(response, first_response)
