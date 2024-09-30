from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class CustomUser(AbstractUser):
    # Adding extra fields without changing the creation process
    LOGIN_TYPE_CHOICES = [
        ('email', 'Email and Password'),
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('apple', 'Apple'),
    ]
    email = models.EmailField(unique=True)
    is_company_owner = models.BooleanField(default=False)
    streak = models.IntegerField(default=0)
    login_type = models.CharField(max_length=50, choices=LOGIN_TYPE_CHOICES, default='email')
    bio = models.TextField(blank=True, null=True)
    # ImageField for file uploads (if user manually uploads a picture)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # URLField for external profile picture URLs (from Google, etc.)
    profile_picture_url = models.URLField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)  # Automatically set when the user is created
    tickets = models.PositiveIntegerField(default=0)
    xp = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.email


class Company(models.Model):
    # This is the company model
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_companies')
    domain = models.URLField(max_length=512)
    members = models.ManyToManyField(CustomUser, through="Membership")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Membership(models.Model):
    # This is the membership model
    ROLE = [
        ("owner", "Owner"),
        ("HR", "HR Manager"),
        ("employee", "Employee"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE, default='employee')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'company') # One member per user per company

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"


class Invitation(models.Model):
    # This is the invitation model
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
    ]
    email = models.EmailField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invite_code = models.CharField(max_length=6, unique=True)  # 6-digit invite code
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')  # The person who invited the employee
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Invite for {self.email} to {self.company}"

