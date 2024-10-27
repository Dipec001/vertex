from django.db import models
from django.contrib.auth.models import AbstractUser
from timezone_field import TimeZoneField
import pytz
import random
# Create your models here.

TIMEZONES = tuple(zip(pytz.all_timezones, pytz.all_timezones))
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
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    # URLField for external profile picture URLs (from Google, etc.)
    profile_picture_url = models.URLField(max_length=2000, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)  # Automatically set when the user is created
    company_tickets = models.PositiveIntegerField(default=0)
    global_tickets = models.PositiveIntegerField(default=0)  # Count of tickets
    streak_savers = models.PositiveIntegerField(default=0)  # Count of streak savers
    xp = models.PositiveIntegerField(default=0)
    gem = models.PositiveIntegerField(default=0)  # Available gems (earned - spent)
    gems_spent = models.PositiveIntegerField(default=0)  # Total gems the user has spent
    # Add a foreign key to the company (a user can only belong to one company)
    company = models.ForeignKey(
        'Company', 
        on_delete=models.CASCADE,  # Delete the user if the company is deleted
        related_name='members',  # Reverse lookup for company.members
        null=True,  # Company is not required
        blank=True  # Company must not be selected
    )
    timezone = TimeZoneField(default='UTC', use_pytz=False)
    # league = models.ForeignKey('LeagueInstance', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.email


class Company(models.Model):
    # This is the company model
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_company')
    domain = models.URLField(max_length=512)
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
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invite_code = models.CharField(max_length=6, unique=True)  # 6-digit invite code
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')  # The person who invited the employee
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Invite for {self.email} to {self.company}"


class Xp(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='xp_records')
    timeStamp = models.DateTimeField(auto_now_add=True)  # Timestamp for when XP is earned
    totalXpToday = models.FloatField(default=0.0)  # XP earned today
    totalXpAllTime = models.FloatField(default=0.0)  # Total XP earned across all time
    gems_awarded = models.PositiveIntegerField(default=0)  # Gems awarded based on XP today

    def __str__(self):
        return f'{self.user.email} - XP: {self.totalXpToday}'
    
    class Meta:
        unique_together = ('user', 'timeStamp')  # Ensure one entry per user per day
    

class Streak(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='streak_records')
    timeStamp = models.DateTimeField(auto_now_add=True)  # Timestamp for the streak update
    currentStreak = models.IntegerField(default=0)  # Current active streak days
    highestStreak = models.IntegerField(default=0)  # Highest streak ever achieved
    currentStreakSaver = models.IntegerField(default=0)  # Optional field for streak savers

    def __str__(self):
        return f'{self.user.email} - Streak: {self.currentStreak}'



class DailySteps(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_steps')
    xp = models.FloatField()  # XP earned from the activity
    step_count = models.IntegerField()  # Steps recorded
    timestamp = models.DateTimeField()  # When the steps were recorded
    date = models.DateField()  # The day these steps are logged

    def __str__(self):
        return f'{self.user.email} - Steps: {self.step_count} on {self.date}'


class WorkoutActivity(models.Model):
    ACTIVITY_TYPE = [
        ("mindfulness", "Mindfulness"),
        ("movement", "Movement"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='workout_activity')
    duration = models.IntegerField()  # Duration in minutes
    xp = models.FloatField()  # XP earned from the activity
    activity_type = models.CharField(max_length=50)  # Type of activity: "Mindfulness" or "Movement"
    activity_name = models.CharField(max_length=100)  # Name of the activity (e.g., Running, Yoga, Steps)
    distance = models.FloatField(null=True, blank=True, default=0.0)  # Distance for movement activities
    average_heart_rate = models.FloatField(null=True, blank=True, default=0.0)  # Average heart rate
    metadata = models.TextField(null=True, blank=True)  # Optional metadata
    start_datetime = models.DateTimeField()  # Start of the activity
    end_datetime = models.DateTimeField()  # End of the activity
    deviceType = models.CharField(max_length=100, null=True, blank=True) # Optional: to store device model it is recorded in

    def __str__(self):
        return f'{self.user.email} - Activity: {self.activity_name} on {self.start_datetime.date()}'


class Purchase(models.Model):
    ITEM_CHOICES = [
        ('streak_saver', 'Streak Saver'),
        ('ticket_global', 'Global Ticket'),
        ('ticket_company', 'Company Ticket'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='purchases')
    item_name = models.CharField(max_length=100, choices=ITEM_CHOICES)  # Make this a choice field
    gem_used = models.PositiveIntegerField(default=1)  # Amount of gem used for the purchase
    quantity = models.PositiveIntegerField(default=1)  # New field to store the quantity of items purchased
    timestamp = models.DateTimeField(auto_now_add=True)  # Timestamp for when the purchase was made

    def __str__(self):
        return f'{self.user.email} - Purchased: {self.quantity} {self.item_name}(s) for {self.gem_used} gem'
    

# Prize Model (for both global and company draws)
class Prize(models.Model):
    draw = models.ForeignKey('Draw', on_delete=models.CASCADE, related_name='prizes')
    name = models.CharField(max_length=255)
    description = models.TextField()
    value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Cash value or item worth
    quantity = models.IntegerField(default=1)  # How many of these prizes exist

    def __str__(self):
        return self.name

class Draw(models.Model):
    DRAW_TYPE_CHOICES = [
        ('company', 'Company Draw'),
        ('global', 'Global Draw'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    draw_name = models.CharField(max_length=255)
    draw_type = models.CharField(max_length=7, choices=DRAW_TYPE_CHOICES)
    draw_date = models.DateTimeField()  # When the draw happens
    number_of_winners = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    video = models.FileField(upload_to='draw_videos/', null=True, blank=True)  # Optional video upload

    def pick_winners(self):
        # Get all entries for the draw
        entries = DrawEntry.objects.filter(draw=self)
        if entries.count() == 0:
            return  # No entries to pick from

        # Randomly pick winners from the list of entries
        winners = random.sample(list(entries), min(self.number_of_winners, entries.count()))

        # Save the winners in the DrawWinner table
        for entry in winners:
            DrawWinner.objects.create(user=entry.user, draw=self)

        # Mark draw as inactive
        self.is_active = False
        self.save()
    
    def __str__(self):
        return f"{self.draw_name} ({self.draw_type})"

# Entry Model (tracks user entries in a draw)
class DrawEntry(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='entries')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} entry for {self.draw}"

# Winner Model (tracks the winners for each draw)
class DrawWinner(models.Model):
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    prize = models.ForeignKey(Prize, on_delete=models.SET_NULL, null=True, blank=True)
    win_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} won {self.prize.name} in {self.draw.draw_name}"
    


class League(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField()  # Ranking order of leagues

    def __str__(self):
        return self.name

class LeagueInstance(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    league_start = models.DateTimeField()  # Track the start of each week
    league_end = models.DateTimeField()
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE)
    max_participants = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.league.name} - {self.league_start}"

class UserLeague(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    league_instance = models.ForeignKey(LeagueInstance, on_delete=models.CASCADE)
    xp_company = models.IntegerField(default=0)  # XP specific to company leagues
    xp_global = models.IntegerField(default=0)    # XP specific to global leagues
    is_retained = models.BooleanField(default=False)  # Grace period flag

    class Meta:
        unique_together = ('user', 'league_instance')
    
    def __str__(self):
        return f"{self.user.username} in {self.league_instance}"