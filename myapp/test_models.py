from django.test import TestCase
from .models import CustomUser, Company, Membership, Invitation
from django.core.exceptions import ValidationError

# Create your tests here.

class CustomUserModelTest(TestCase):

    def setUp(self):
        """Create a CustomUser instance for testing"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123',
            is_company_owner=True,
            streak=10,
            login_type='email',
            bio='A test user',
            tickets=5,
            xp=100
        )

    def test_user_creation(self):
        """Test if a user is created with the correct data"""
        self.assertEqual(self.user.email, 'testuser@example.com')
        self.assertEqual(self.user.is_company_owner, True)
        self.assertEqual(self.user.streak, 10)
        self.assertEqual(self.user.login_type, 'email')
        self.assertEqual(self.user.bio, 'A test user')
        self.assertEqual(self.user.tickets, 5)
        self.assertEqual(self.user.xp, 100)

    def test_user_str(self):
        """Test the string representation of the user"""
        self.assertEqual(str(self.user), 'testuser@example.com')

    def test_profile_picture(self):
        """Test if profile picture field works correctly"""
        self.user.profile_picture_url = "http://example.com/profile.jpg"
        self.user.save()
        self.assertEqual(self.user.profile_picture_url, "http://example.com/profile.jpg")


    def test_user_invalid_email(self):
        """Test creating a user with an invalid email."""
        user = CustomUser(email="invalidemail", username="testuser")
        with self.assertRaises(ValidationError):
            user.full_clean()  # This will run Django's model validation, including email validation

    def test_blank_user_email(self):
        """Test creating a user without an email (should fail)."""
        user = CustomUser(email="", username="testuser")
        with self.assertRaises(ValidationError):
            user.full_clean()  # Blank email should raise a ValidationError

    def test_blank_company_name(self):
        """Test creating a company without a name."""
        owner = CustomUser.objects.create(username="owner", email="owner@test.com")
        company = Company(name="", owner=owner, domain="https://testdomain.com")
        with self.assertRaises(ValidationError):
            company.full_clean()  # Blank company name should raise a ValidationError

    def test_streak_cannot_be_negative(self):
        """Test that the streak cannot be a negative value."""
        user = CustomUser(email="testuser@test.com", username="testuser", streak=-1)
        with self.assertRaises(ValidationError):
            user.full_clean()  # Negative streak should raise a ValidationError

    def test_xp_cannot_be_negative(self):
        """Test that xp cannot be a negative value."""
        user = CustomUser(email="testuser@test.com", username="testuser", xp=-10)
        with self.assertRaises(ValidationError):
            user.full_clean()  # Negative xp should raise a ValidationError

    def test_tickets_cannot_be_negative(self):
        """Test that tickets cannot be a negative value."""
        user = CustomUser(email="testuser@test.com", username="testuser", tickets=-5)
        with self.assertRaises(ValidationError):
            user.full_clean()  # Negative tickets should raise a ValidationError

class CompanyModelTest(TestCase):

    def setUp(self):
        """Create a Company instance for testing"""
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpassword123'
        )
        self.company = Company.objects.create(
            name="Test Company",
            owner=self.owner,
            domain="https://testcompany.com"
        )

    def test_company_creation(self):
        """Test if a company is created with the correct data"""
        self.assertEqual(self.company.name, "Test Company")
        self.assertEqual(self.company.owner.email, "owner@example.com")
        self.assertEqual(self.company.domain, "https://testcompany.com")

    def test_company_str(self):
        """Test the string representation of the company"""
        self.assertEqual(str(self.company), "Test Company")



class MembershipModelTest(TestCase):

    def setUp(self):
        """Create Membership instances for testing"""
        self.user = CustomUser.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='testpassword123'
        )
        self.company = Company.objects.create(
            name="Test Company",
            owner=self.user,
            domain="https://testcompany.com"
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="employee"
        )

    def test_membership_creation(self):
        """Test if a membership is created with the correct data"""
        self.assertEqual(self.membership.user.email, 'employee@example.com')
        self.assertEqual(self.membership.company.name, 'Test Company')
        self.assertEqual(self.membership.role, 'employee')

    def test_membership_str(self):
        """Test the string representation of the membership"""
        self.assertEqual(str(self.membership), "employee@example.com - Test Company (employee)")

    def test_unique_membership(self):
        """Test that a user cannot belong to the same company more than once"""
        with self.assertRaises(Exception):
            Membership.objects.create(user=self.user, company=self.company)



class InvitationModelTest(TestCase):

    def setUp(self):
        """Create an Invitation instance for testing"""
        self.inviter = CustomUser.objects.create_user(
            username='inviter',
            email='inviter@example.com',
            password='testpassword123'
        )
        self.company = Company.objects.create(
            name="Test Company",
            owner=self.inviter,
            domain="https://testcompany.com"
        )
        self.invitation = Invitation.objects.create(
            email='newuser@example.com',
            first_name='New',
            last_name='User',
            company=self.company,
            invite_code='ABC123',
            invited_by=self.inviter,
            status='pending'
        )

    def test_invitation_creation(self):
        """Test if an invitation is created with the correct data"""
        self.assertEqual(self.invitation.email, 'newuser@example.com')
        self.assertEqual(self.invitation.first_name, 'New')
        self.assertEqual(self.invitation.last_name, 'User')
        self.assertEqual(self.invitation.invite_code, 'ABC123')
        self.assertEqual(self.invitation.status, 'pending')

    def test_invitation_str(self):
        """Test the string representation of the invitation"""
        self.assertEqual(str(self.invitation), " Invite for newuser@example.com to Test Company")



