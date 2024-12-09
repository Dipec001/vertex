from unittest import skipIf

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
        response = self.client.get(self.url)
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
        self.assertEqual(int(company_stats['avg_xp_per_user']), 151)

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

        # Test week ago stats
        week_ago_stats = next(
            (stats for stats in daily_stats if stats['date'] == self.week_ago.isoformat()),
            None
        )
        self.assertIsNotNone(week_ago_stats)
        self.assertEqual(week_ago_stats['total_steps'], 11000)  # 4500 + 6500
        self.assertEqual(week_ago_stats['total_xp'], 280)  # 120 + 160

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
        # allways return 30 datas with zeros values
        self.assertEqual(len(data['daily_stats']), 30)
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
@skipIf(not settings.DEBUG, "Skip tests in production environment")
class EmployeeByCompanyModelViewTest(APITestCase):
    def setUp(self):
        # Create a company owner
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