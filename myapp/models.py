from django.db import models
from django.contrib.auth.models import AbstractUser
from timezone_field import TimeZoneField
import pytz
import random
from django.db.models import Sum
from django.utils.timezone import now
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
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
    streak_savers = models.PositiveIntegerField(default=0)  # Count of streak savers
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

    def get_gem_count(self):
        # Calculate total gems (XP-based + manual gems)
        total_xp_gems = Gem.objects.filter(user=self).aggregate(total_xp_gems=Sum('xp_gem'))['total_xp_gems'] or 0
        total_manual_gems = Gem.objects.filter(user=self).aggregate(total_manual_gems=Sum('manual_gem'))['total_manual_gems'] or 0
        total_gems_spent = self.gems_spent  # Assuming you have a `gems_spent` field

        # Calculate total gems and ensure no negative gems
        total_gems = total_xp_gems + total_manual_gems - total_gems_spent
        return max(0, total_gems)  # Ensure no negative gems
    
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
    # Only needed after the user signup. Associate it to the user after signup
    invited_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')  # The person who invited the employee
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Invite for {self.email} to {self.company}"

class Gem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='gem_records')
    date = models.DateField()
    xp_gem = models.PositiveIntegerField(default=0, blank=True, null=True)
    manual_gem = models.PositiveIntegerField(default=0, blank=True, null=True)
    copy_xp_gem = models.PositiveIntegerField(default=0, blank=True, null=True)
    copy_manual_gem = models.PositiveIntegerField(default=0, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.email} - Gems on {self.date}'

    def save(self, *args, **kwargs):
        # Track whether the values have changed
        changed = False

        if self.pk is not None:
            orig = Gem.objects.get(pk=self.pk)
            if self.xp_gem != orig.xp_gem or self.manual_gem != orig.manual_gem:
                changed = True
        else:
            # New object, always consider it as changed
            changed = True

        super().save(*args, **kwargs)

        # Only broadcast if values have actually changed
        if changed:
            self.broadcast_gem_update()

    def broadcast_gem_update(self):
        user = self.user
        new_gem_count = user.get_gem_count()  # Use the `get_gem_count` method to get the total gems

        # Calculate the remaining XP gems the user can earn today
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone)
        today = user_local_time.date()

        gem_record = Gem.objects.filter(user=user, date=today).first()
        gems_earned_today = gem_record.xp_gem if gem_record else 0
        xp_gems_remaining_today = max(0, 5 - gems_earned_today)  # Assuming the daily limit is 5

        # Get the channel layer and send the updated gem count and XP gems remaining to the WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'gem_{user.id}',  # Group name based on user_id
            {
                'type': 'send_gem_update',
                'gem_count': new_gem_count,  # Send the new gem count
                'xp_gems_remaining_today': xp_gems_remaining_today,  # Send the remaining XP gems for today
            }
        )



class Xp(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='xp_records')
    timeStamp = models.DateTimeField()  # Timestamp for when XP is earned
    date = models.DateField()  # Explicitly store the date part
    totalXpToday = models.FloatField(default=0.0)  # XP earned today
    totalXpAllTime = models.FloatField(default=0.0)  # Total XP earned across all time
    gems_awarded = models.PositiveIntegerField(default=0)  # Gems awarded based on XP today

    def __str__(self):
        return f'{self.user.email} - XP: {self.totalXpToday}'
    
    class Meta:
        unique_together = ('user', 'date')  # Ensure one entry per user per day
    
    def save(self, *args, **kwargs):
        self.gems_awarded = int (self.totalXpToday // 250)
        if not self.date:
            self.date = self.timeStamp.date()  # Set the date field based on timeStamp
        super(Xp, self).save(*args, **kwargs)

class Streak(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='streak_records')
    timeStamp = models.DateTimeField()  # Timestamp for the streak update
    date = models.DateField()  # Explicitly store the date part
    currentStreak = models.IntegerField(default=0)  # Current active streak days
    highestStreak = models.IntegerField(default=0)  # Highest streak ever achieved
    streak_saved = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.user.email} - Streak: {self.currentStreak}'
    
    class Meta:
        unique_together = ('user', 'date')  # Ensure one entry per user per day
    
    def save(self, *args, **kwargs):
        if not self.date:
            self.date = self.timeStamp.date()  # Set the date field based on timeStamp
        super(Streak, self).save(*args, **kwargs)



class DailySteps(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_steps')
    xp = models.FloatField()  # XP earned from the activity
    step_count = models.IntegerField()  # Steps recorded
    timestamp = models.DateTimeField()  # When the steps were recorded in local time
    date = models.DateField()  # Local day these steps are logged

    def __str__(self):
        return f'{self.user.email} - Steps: {self.step_count} on {self.date}'
    
    class Meta:
        unique_together = ('user', 'date')  # Ensure one record per user per day


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
    
    class Meta:
        unique_together = ('user', 'start_datetime')  # Ensure one record per user per start time
    


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
    draw = models.ForeignKey('Draw', on_delete=models.CASCADE, related_name='prizes', null=True)
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

        # Get available prizes for the draw
        # prizes = list(Prize.objects.filter(draw=self, quantity__gt=0).order_by('-value'))  # Prioritize by value or other criteria
        prizes = list(Prize.objects.filter(draw=self, quantity__gt=0))

        # Randomly pick winners from the list of entries
        winners = random.sample(list(entries), min(self.number_of_winners, entries.count()))

        # Assign prizes to winners
        for i, entry in enumerate(winners):
            if prizes:  # If there are remaining prizes
                prize = prizes.pop(0)  # Get the first prize from the list
                prize.quantity -= 1  # Reduce prize quantity
                prize.save()

                # If there are still quantities left, add it back to the list
                if prize.quantity > 0:
                    prizes.append(prize)
            else:
                prize = None  # No prize available for this winner

            # Create the DrawWinner entry
            DrawWinner.objects.create(user=entry.user, draw=self, prize=prize)

        # Mark draw as inactive
        self.is_active = False
        self.save()
    
    def __str__(self):
        return f"{self.draw_name} ({self.draw_type})"
    

class DrawImage(models.Model):
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='images')
    image_link = models.URLField(max_length=255)  # Store the image URL
    title = models.CharField(max_length=255)  # Title for the image

    def __str__(self):
        return self.title

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
        prize_name = self.prize.name if self.prize else "But No Prize Allocated"
        return f"{self.user} won {prize_name} in {self.draw.draw_name}"

    


class League(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField()  # Ranking order of leagues

    def __str__(self):
        return self.name

class LeagueInstance(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    league_start = models.DateTimeField()  # Track the start of each week
    league_end = models.DateTimeField(db_index=True)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE,db_index=True)
    max_participants = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True,db_index=True)

    def __str__(self):
        return f"{self.league.name} - {self.league_start}"

class UserLeague(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    league_instance = models.ForeignKey(LeagueInstance, on_delete=models.CASCADE)
    xp_company = models.IntegerField(default=0)  # XP specific to company leagues
    xp_global = models.IntegerField(default=0)    # XP specific to global leagues

    class Meta:
        unique_together = ('user', 'league_instance')
    
    def __str__(self):
        return f"{self.user.username} in {self.league_instance}"


class UserFollowing(models.Model):
    follower =models.ForeignKey(CustomUser, on_delete=models.CASCADE ,related_name="following")
    following = models.ForeignKey(CustomUser,on_delete=models.CASCADE, related_name="followers")
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ["-followed_at"]

    def __str__(self):
        return f"{self.follower} follows {self.following}"
    

class Feed(models.Model):
    PROMOTION = 'Promotion'
    MILESTONE = 'Milestone'
    STREAK = 'Streak'
    PRIZE = 'Prize'
    ACTIVITY_MOVEMENT = 'activity_movement'
    ACTIVITY_MINDFUL = 'activity_mindful'


    FEED_TYPES = [
        (PROMOTION, 'Promotion'),
        (MILESTONE, 'Milestone'),
        (STREAK, 'Streak'),
        (PRIZE, 'Prize'),
        (ACTIVITY_MOVEMENT, 'Activity_Movement'),
        (ACTIVITY_MINDFUL, 'Activity_Mindful'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    feed_type = models.CharField(max_length=30, choices=FEED_TYPES)  # Add the feed type
    feed_detail = models.TextField(max_length=1000, blank=True, null=True)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    claps_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.content
    
    # Optionally, calculate likes count dynamically
    def calculate_claps_count(self):
        return self.claps.count()
    

class Clap(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='claps')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'feed')  # Ensures one clap per user per feed

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.feed.claps_count = self.feed.claps.count()
        self.feed.save()

    def delete(self, *args, **kwargs):
        feed = self.feed
        super().delete(*args, **kwargs)
        feed.claps_count = feed.claps.count()
        feed.save()

    def __str__(self):
        return f"Clap on {self.feed}"


class Notif(models.Model):
    # Define constants for each notification type
    RECEIVED_GEM = "received_gem", "Received Gem"
    LEAGUE_PROMOTION = "league_promotion", "League Promotion"
    LEAGUE_DEMOTION = "league_demotion", "League Demotion"
    LEAGUE_RETAINED = "league_retained", "League Retained"
    PURCHASE_COMPANY_DRAW = "purchase_companydraw", "Purchase Company Draw"
    PURCHASE_GLOBAL_DRAW = "purchase_globaldraw", "Purchase Global Draw"
    PURCHASE_STREAK_SAVER = "purchase_streaksaver", "Purchase Streak Saver"

    # Define the tuple list
    NOTIF_TYPES = [
        RECEIVED_GEM,
        LEAGUE_PROMOTION,
        LEAGUE_DEMOTION,
        LEAGUE_RETAINED,
        PURCHASE_COMPANY_DRAW,
        PURCHASE_GLOBAL_DRAW,
        PURCHASE_STREAK_SAVER,
    ]


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    content = models.TextField(max_length=1024)
    notif_type = models.CharField(max_length=50, choices=NOTIF_TYPES)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.notif_type}: {self.content}"



class ActiveSession(models.Model): 
    TOKEN_TYPES = [
        ('access', 'Access'),
        ('refresh', 'Refresh'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    token = models.CharField(max_length=255) 
    token_type = models.CharField(choices=TOKEN_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)