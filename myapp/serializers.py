from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (Company, Invitation, Membership, WorkoutActivity, Xp, Streak, DailySteps, Purchase, Draw,
                     DrawEntry, DrawWinner, Prize, UserLeague, Feed, Clap, UserFollowing, Gem, DrawImage, Notif)
import random
import string
from allauth.socialaccount.models import SocialAccount
import logging
from rest_framework.validators import UniqueValidator
from django.db import transaction, IntegrityError
from .tasks import send_invitation_email_task
from timezone_field.rest_framework import TimeZoneSerializerField
from datetime import datetime, timedelta, timezone
from django.db.models import Sum
from zoneinfo import ZoneInfo
from django.utils import timezone as t


logger = logging.getLogger(__name__)

CustomUser = get_user_model()
class EmployeeSerializer(serializers.ModelSerializer):
    downloaded_the_app = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', "company",
                  "downloaded_the_app", "last_login"]

    def get_downloaded_the_app(self, obj: CustomUser):
        return obj.last_login is not None


class CompanySerializer(serializers.ModelSerializer):
    total_employees = serializers.IntegerField(read_only=True, default=0)
    class Meta:
        model = Company
        fields = ['id', 'name', 'owner', 'domain','total_employees', 'created_at']



class CompanyOwnerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=CustomUser.objects.all())],  # Ensure email is unique at the serializer level
    )
    company_name = serializers.CharField(max_length=255, required=True)
    domain = serializers.URLField(max_length=512, required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'company_name', 'domain']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},  # Ensure password is marked as required
        }

    def generate_unique_username(self, email):
        base_username = email.split('@')[0]
        username = base_username
        counter = 1

        # Check if username already exists, and append a counter if it does
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        return username

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        company_name = validated_data['company_name']
        domain = validated_data.get('domain', '')  # Get domain or set it to an empty string if not provided

        # Extract the email prefix to use as the username
        username = self.generate_unique_username(email)

        # Create the user and set `is_company_owner` to True
        user = CustomUser.objects.create_user(email=email, username=username, password=password, is_company_owner=True)

        # Create the company and associate it with the owner
        company = Company.objects.create(name=company_name, owner=user, domain=domain)

        # Now, assign the company to the user
        user.company = company
        # Set the username as the email prefix
        user.username = username
        user.save()

         # Add the owner as a member of the company
        Membership.objects.create(user=user, company=company, role="owner")


        return user, company

class InvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.StringRelatedField(read_only=True)  # Make this field read-only

    class Meta:
        model = Invitation
        fields = ['email','first_name','last_name', 'invite_code', 'status', 'date_sent','invited_by']
        read_only_fields = ['invite_code', 'status', 'date_sent', 'invited_by']  # Mark these as read-only for creatio

    def create(self, validated_data):
        email = validated_data['email']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        user = self.context['request'].user  # The user sending the invitation
        company = self.context['company']  # Pass the company from the view

        # Check if the user is trying to invite themselves
        if email.lower() == user.email.lower():
            raise serializers.ValidationError({"error": "You cannot invite yourself."})

        # Prevent inviting an existing user who already belongs to a company
        if CustomUser.objects.filter(email=email, company__isnull=False).exists():
            raise serializers.ValidationError({"error": "The user is already a member of a company."})

        # Check if the user has already been invited to this company
        existing_invitation = Invitation.objects.filter(email=email, company=company).first()

        if existing_invitation:
            # Send a reminder email asynchronously
            send_invitation_email_task.delay_on_commit(
                invite_code=existing_invitation.invite_code,
                company_name=company.name,
                inviter_name=user.username,
                to_email=email
            )
            return existing_invitation  # Return the existing invitation object
        else:
            # Generate a 6-digit numeric code
            invite_code = ''.join(random.choices(string.digits, k=6))

            # Send the invitation email asynchronously
            send_invitation_email_task.delay_on_commit(
                invite_code=invite_code,
                company_name=company.name,
                inviter_name=user.username,
                to_email=email
            )

            # Create the invitation
            invitation = Invitation.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                invite_code=invite_code,
                invited_by=self.context['request'].user
            )

            return invitation


class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    company = serializers.CharField(source='company.name', read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    streak = serializers.IntegerField(read_only=True)
    streak_savers = serializers.IntegerField(read_only=True)  # Include streak savers
    # gem = serializers.IntegerField(read_only=True)
    gem = serializers.SerializerMethodField()  # Custom field to calculate the total gems
    global_league = serializers.SerializerMethodField()
    company_league = serializers.SerializerMethodField()
    follower_count = serializers.IntegerField(source='followers.count', read_only=True)
    following_count = serializers.IntegerField(source='following.count', read_only=True)
    is_following = serializers.SerializerMethodField()
    weekly_xp = serializers.SerializerMethodField()
    weekly_steps = serializers.SerializerMethodField()
    weekly_workouts = serializers.SerializerMethodField()
    total_xp_all_time = serializers.SerializerMethodField()


    class Meta:
        model = CustomUser
        # Include all fields except the raw profile_picture and profile_picture_url
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_company_owner',
            'gem',
            'streak',
            'streak_savers',
            'bio',
            'date_joined',
            'profile_picture_url',  # Custom field with logic
            'company',
            'global_league',
            'company_league',
            'follower_count',
            'following_count',
            'is_following',
            'weekly_xp',
            'weekly_steps',
            'weekly_workouts',
            'total_xp_all_time'
        ]

    def get_gem(self, obj):
        # Calculate the total gems from the Gem model
        total_xp_gems = Gem.objects.filter(user=obj).aggregate(total_xp_gems=Sum('xp_gem'))['total_xp_gems'] or 0
        total_manual_gems = Gem.objects.filter(user=obj).aggregate(total_manual_gems=Sum('manual_gem'))['total_manual_gems'] or 0
        total_gems_spent = obj.gems_spent  # Assuming you have a `gems_spent` field in the user model

        # Calculate total gems
        total_gems = total_xp_gems + total_manual_gems - total_gems_spent
        return max(0, total_gems)  # Ensure no negative gems

    def get_global_league(self, obj):
        # Get the UserLeague entry for the user's global league
        user_league_entry = UserLeague.objects.filter(user=obj, league_instance__company__isnull=True, league_instance__is_active=True).first()
        if user_league_entry:
            return user_league_entry.league_instance.league.name  # Return the league name
        return None

    def get_company_league(self, obj):
        # Get the UserLeague entry for the user's company league
        user_league_entry = UserLeague.objects.filter(user=obj, league_instance__company__isnull=False, league_instance__is_active=True).first()
        if user_league_entry:
            return user_league_entry.league_instance.league.name  # Return the league name
        return None

    def get_profile_picture_url(self, obj):
        # If the user has an uploaded profile picture, return its URL
        if obj.profile_picture:
            return obj.profile_picture.url

        # If the user has provided an external profile picture URL, return it
        if obj.profile_picture_url:
            return obj.profile_picture_url

        # Fallback to a default image if neither is set
        # return '/static/images/default_avatar.png

    def get_is_following(self, obj):
        # Check if the current authenticated user follows the queried user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFollowing.objects.filter(follower=request.user, following=obj).exists()
        return False

    def get_weekly_xp(self, obj):
        return self.get_weekly_data(obj, 'xp_records', 'totalXpToday')

    def get_weekly_steps(self, obj):
        return self.get_weekly_data(obj, 'daily_steps', 'step_count')

    def get_weekly_workouts(self, obj):
        return self.get_detailed_weekly_workouts(obj)

    def get_total_xp_all_time(self, obj):
        # Summing all XP values across all time for the user
        total_xp = Xp.objects.filter(user=obj).aggregate(total=Sum('totalXpToday'))['total'] or 0
        return total_xp

    def get_weekly_data(self, obj, related_field, value_field, use_timestamp=False):
        """Helper to get weekly data from Monday to Sunday, supports timestamp fields."""
        user_timezone = obj.timezone
        current_utc_time = t.now()
        user_local_time = current_utc_time.astimezone(user_timezone)
        current_day = user_local_time.date()

        # Calculate the start and end of the week based on Monday as the start of the week
        start_of_week = current_day - timedelta(days=current_day.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Initialize weekly data as a dictionary with days of the week as keys and 0 values
        weekly_data = {day: 0 for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}

        # Get the user's records for the current week, filter by date range
        records = getattr(obj, related_field)

        # Filter records by date or timestamp based on the field type
        if use_timestamp:
            # For `workout_activity`, filter by `start_datetime` range
            records = records.filter(start_datetime__date__range=[start_of_week, end_of_week])
        else:
            records = records.filter(date__range=[start_of_week, end_of_week])

        # Loop over the records and populate weekly data
        for record in records:
            record_date = record.start_datetime.date() if use_timestamp else record.date
            record_day = record_date.weekday()  # Monday=0, Sunday=6
            weekday_name = list(weekly_data.keys())[record_day]
            weekly_data[weekday_name] += getattr(record, value_field, 0)

        # Set future days of the week to 0
        for day_offset in range(current_day.weekday() + 1, 7):
            weekday_name = list(weekly_data.keys())[day_offset]
            weekly_data[weekday_name] = 0

        return weekly_data

    def get_detailed_weekly_workouts(self, obj):
        user_timezone = obj.timezone
        current_utc_time = t.now()
        user_local_time = current_utc_time.astimezone(user_timezone)
        current_day = user_local_time.date()

        start_of_week = current_day - timedelta(days=current_day.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        weekly_workouts = {day: [] for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}

        workouts = obj.workout_activity.filter(start_datetime__date__range=[start_of_week, end_of_week])

        for workout in workouts:
            workout_day = workout.start_datetime.date().weekday()
            weekday_name = list(weekly_workouts.keys())[workout_day]
            weekly_workouts[weekday_name].append({
                "activity_type": workout.activity_type,
                "activity_name": workout.activity_name,
                "duration": workout.duration,
                "xp": workout.xp,
                "average_heart_rate": workout.average_heart_rate,
                "distance": workout.distance,
                "metadata": workout.metadata,
                "start_datetime": workout.start_datetime,
                "end_datetime": workout.end_datetime,
                "device_type": workout.deviceType,
            })

        # Set future days of the week to an empty list
        for day_offset in range(current_day.weekday() + 1, 7):
            weekday_name = list(weekly_workouts.keys())[day_offset]
            weekly_workouts[weekday_name] = []

        return weekly_workouts


class UpdateProfileSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)  # Change to False if you want `zoneinfo` objects
    class Meta:
        model = CustomUser
        fields = ['username', 'bio', 'profile_picture', 'timezone']



# Serializer for Feed model
class FeedSerializer(serializers.ModelSerializer):
    has_clapped = serializers.SerializerMethodField()
    claps_count = serializers.IntegerField(read_only=True)
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Feed
        fields = ['id', 'user','feed_type','feed_detail', 'content', 'created_at', 'claps_count', 'has_clapped','profile_picture']

    def get_has_clapped(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Clap.objects.filter(user=user, feed=obj).exists()
        return False

    def get_profile_picture(self, obj):
        user = obj.user
        if user.profile_picture:
            return user.profile_picture.url
        elif user.profile_picture_url:
            return user.profile_picture_url
        return None



# Serializer for Clap model
class ClapSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = Clap
        fields = ['id', 'user', 'feed', 'created_at']


# Serializer for UserFollowing model
class UserFollowingSerializer(serializers.ModelSerializer):
    follower = UserProfileSerializer(read_only=True)
    following = UserProfileSerializer(read_only=True)
    followed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = UserFollowing
        fields = ['follower', 'following', 'followed_at']


class NormalUserSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    profile_picture = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    invitation_id = serializers.IntegerField(required=True)  # Include invitation_id for validation
    password = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)  # Make password optional
    login_type = serializers.ChoiceField(choices=CustomUser.LOGIN_TYPE_CHOICES, required=True)
    uid = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # UID for social logins
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'username', 'profile_picture', 'invitation_id', 'login_type', 'uid', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Check if email already exists
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists.")

        # Check if username is unique
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists.")


        # Check login type to validate password
         # Validate login_type and corresponding fields
        login_type = data.get('login_type')

        # If it's an email signup, password is required
        if login_type == 'email':
            if not data.get('password'):
                raise serializers.ValidationError("Password is required for email signups.")

        # For social logins, UID is required
        elif login_type in ['google', 'facebook', 'apple']:
            if not data.get('uid'):
                raise serializers.ValidationError(f"UID is required for {login_type} signups.")

        return data

    @transaction.atomic  # Wrap the method in an atomic transaction
    def create(self, validated_data):
        profile_picture = validated_data.pop('profile_picture', None)
        invitation_id = validated_data.pop('invitation_id')  # Get the invitation ID
        login_type = validated_data.pop('login_type')
        uid = validated_data.pop('uid', None)  # UID might be None for email signup
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')

        # Create user based on login type
        if login_type in ['google', 'facebook', 'apple']:
            # Check if a SocialAccount with this provider and UID already exists
            if SocialAccount.objects.filter(provider=login_type, uid=uid).exists():
                raise serializers.ValidationError(f"A user with this {login_type} UID already exists.")

        # Create user based on login type
        # if login_type in ['google', 'facebook', 'apple']:
        #     # social sign up
            user = CustomUser.objects.create_user(
                email=validated_data['email'],
                password=None,  # Social users don't need a password
                username=validated_data['username'],
                login_type=login_type,
                first_name=first_name,
                last_name=last_name
            )

            # Create the SocialAccount entry
            SocialAccount.objects.create(
                user=user,
                uid=uid,
                provider=login_type,  # Use the correct provider
                extra_data={'email': validated_data['email'], 'picture': profile_picture or ''}
            )
        else:
            user = CustomUser.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                username=validated_data['username']
            )

        if profile_picture:
            user.profile_picture_url = profile_picture
            user.save()

        # Now, associate the user with the company and mark the invitation as accepted
        try:
            invitation = Invitation.objects.get(id=invitation_id, status='pending')  # Fetch the invitation
            # Mark the invitation as accepted
            invitation.status = 'accepted'
            invitation.save()

            # Set the user's company to the invited company
            user.company = invitation.company  # Directly associate the user with the company
            user.save()  # Save the user to update their company

            # Create a membership entry for the user in the company
            Membership.objects.create(
                user=user,
                company=invitation.company,
                role='employee'  # Default role as 'employee' or any role you prefer
            )
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation ID.")

        return user


class DailyStepsSerializer(serializers.ModelSerializer):
    xp = serializers.FloatField(read_only=True)

    class Meta:
        model = DailySteps
        fields = ['step_count', 'timestamp', 'date', 'xp']
        extra_kwargs = {
            'timestamp': {'required': True},
            'date': {'required': False}
        }

    def validate_timestamp(self, value):
        user = self.context['request'].user
        # Existing validation
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise serializers.ValidationError("Invalid datetime format. Expected format: YYYY-MM-DDTHH:MM:SS")
        elif not isinstance(value, datetime):
            raise serializers.ValidationError("Invalid type for timestamp. Expected str or datetime.")

        # New validation for join date
        if value.date() < user.date_joined.date():
            raise serializers.ValidationError("Timestamp cannot be before the user’s join date.")

        return value

    def validate_step_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Step count cannot be negative.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        print(user.email)
        step_count = validated_data.get('step_count')
        timestamp = validated_data.get('timestamp')
        print(timestamp, 'here is the timestamp passed')

        with transaction.atomic():
            local_date = timestamp.date()
            try:
                daily_steps, created = DailySteps.objects.get_or_create(
                    user=user,
                    date=local_date,
                    defaults={'xp': step_count / 10, 'timestamp': timestamp, **validated_data}
                )

                new_xp = 0
                if created:
                    new_xp = step_count / 10
                    daily_steps.xp = new_xp
                else:
                    if step_count > daily_steps.step_count:
                        step_diff = step_count - daily_steps.step_count
                        new_xp = step_diff / 10
                        daily_steps.step_count = step_count
                        daily_steps.xp += new_xp
                        daily_steps.timestamp = max(daily_steps.timestamp, timestamp)
                    else:
                        raise serializers.ValidationError(
                            f"No update was made; step count is less than or equal to the latest entry for this day, {daily_steps.step_count} steps."
                        )

                daily_steps.save()
                self.update_user_leagues(user, new_xp, xp_date=timestamp)
                self.update_user_xp(user, local_date, new_xp, timestamp)
                self.create_workout_activity(user, new_xp, timestamp)

                # Query the total daily steps after updating/creating the entry
                total_daily_step_count = DailySteps.objects.filter(user=user).aggregate(
                    total_steps=Sum('step_count')
                )['total_steps'] or 0

                # Check milestones dynamically based on the total daily steps
                self.check_dynamic_milestones(user, total_daily_step_count)

                return daily_steps
            except Exception as e:
                logger.error(f"Error creating/updating DailySteps for user {user.id}: {str(e)}")
                raise serializers.ValidationError(f"An error occurred while processing the request:{str(e)}")

    def update_user_leagues(self, user, new_xp, xp_date):
        active_leagues = UserLeague.objects.filter(
            user=user,
            league_instance__is_active=True
        ).select_related('league_instance__company')

        for user_league in active_leagues:
            league_instance = user_league.league_instance
            league_start_date = league_instance.league_start

            user_timezone = ZoneInfo(user.timezone.key)
            xp_date_local = xp_date.replace(tzinfo=user_timezone)
            xp_date_utc = xp_date_local.astimezone(timezone.utc)

            if xp_date_utc >= league_start_date:
                if league_instance.company is not None:
                    user_league.xp_company += new_xp
                else:
                    user_league.xp_global += new_xp
                user_league.save()


    def update_user_xp(self, user, date, new_xp, timestamp):
        user_xp, created_xp = Xp.objects.get_or_create(
            user=user,
            date=date,
            defaults={
                'timeStamp': timestamp
            }
        )
        if not created_xp and new_xp > 0:
            user_xp.totalXpToday += new_xp
            user_xp.totalXpAllTime += new_xp
            user_xp.save()
        elif created_xp:
            user_xp.totalXpToday = new_xp
            user_xp.totalXpAllTime += new_xp
            user_xp.save()

    def create_workout_activity(self, user, new_xp, timestamp):
        if new_xp > 0:
            # Determine the date from the provided timestamp
            local_date = timestamp.date()

            try:
                # Try to retrieve an existing workout for steps on the same day
                workout_activity = WorkoutActivity.objects.filter(
                    user=user,
                    activity_type="movement",
                    activity_name="steps",
                    start_datetime__date=local_date
                ).first()

                if workout_activity:
                    # Update the existing workout activity
                    workout_activity.xp += new_xp
                    # workout_activity.step_count += step_count  # Assuming `step_count` is recorded
                    workout_activity.end_datetime = max(workout_activity.end_datetime, timestamp)
                    workout_activity.save()
                else:
                    # Create a new workout activity if none exists for the day
                    WorkoutActivity.objects.create(
                        user=user,
                        activity_type="movement",
                        activity_name="steps",
                        xp=new_xp,
                        duration=0,
                        distance=0,
                        average_heart_rate=0,
                        start_datetime=timestamp,
                        end_datetime=timestamp,
                        metadata='{}',
                        deviceType=None
                    )
            except IntegrityError:
                raise serializers.ValidationError(f"An error occurred while recording steps workout activity for {timestamp}.")

    def check_dynamic_milestones(self, user, total_daily_step_count, milestone_increment=10000):
        """
        Check milestones dynamically and create a feed only if the milestone hasn't been reached before.
        """
        milestone = milestone_increment
        last_feed = Feed.objects.filter(user=user, feed_type=Feed.MILESTONE).order_by('-created_at').first()
        print(last_feed.content, 'last milestone content')
        last_milestone = int(last_feed.content.split(" ")[-2]) if last_feed else 0
        print("last milestone", last_milestone)

        while milestone <= total_daily_step_count:
            if milestone > last_milestone:
                Feed.objects.create(
                    user=user,
                    feed_type=Feed.MILESTONE,
                    content=f"{user.username} has achieved a personal bonus of {milestone} steps!",
                )
                print(f"Feed created for {milestone}-step milestone.")
            milestone += milestone_increment


class WorkoutActivitySerializer(serializers.ModelSerializer):
    xp = serializers.FloatField(read_only=True)  # Mark xp as read-only

    class Meta:
        model = WorkoutActivity
        fields = [
            'id',
            'duration',
            'xp',
            'activity_type',
            'activity_name',
            'distance',
            'average_heart_rate',
            'metadata',
            'start_datetime',
            'end_datetime',
            'deviceType',
        ]


    def validate(self, data):
        """Custom validation for start/end times and join date."""
        user = self.context['request'].user
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')

        # Existing validation
        if start_datetime is None or end_datetime is None:
            raise serializers.ValidationError("Invalid date format for start_datetime or end_datetime.")
        if end_datetime <= start_datetime:
            raise serializers.ValidationError("End time must be after the start time.")

        # New validation for join date
        if start_datetime.date() < user.date_joined.date() or end_datetime.date() < user.date_joined.date():
            raise serializers.ValidationError("Activity dates cannot be before the user’s join date.")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        start_datetime = validated_data['start_datetime']
        end_datetime = validated_data['end_datetime']

        if (WorkoutActivity.objects.filter(
            user=user,
            start_datetime=start_datetime,
            end_datetime=end_datetime
        ).exists()):
            raise serializers.ValidationError("A workout with the same start and end times already exists for this day.")

        xp_earned = self.calculate_xp(validated_data)
        validated_data['xp'] = xp_earned
        workout_activity = WorkoutActivity.objects.create(user=user, **validated_data)
        self.update_xp(workout_activity)
        self.update_user_leagues(user, xp_earned, xp_date=start_datetime)
        return workout_activity

    def calculate_xp(self, data):
        duration = data.get('duration', 0)
        activity_type = data.get('activity_type')
        movement_xp = 0
        if activity_type == 'movement':
            if duration >= 60:
                movement_xp += 200
            elif duration >= 45:
                movement_xp += 150
            elif duration >= 30:
                movement_xp += 100
            avg_bpm = data.get('average_heart_rate', 0)
            if 100 <= avg_bpm < 120:
                movement_xp += 20
            elif 120 <= avg_bpm < 150:
                movement_xp += 40
            elif avg_bpm >= 150:
                movement_xp += 60
        elif activity_type == 'mindfulness':
            if data['activity_name'] == 'Yoga':
                if duration >= 60:
                    movement_xp += 200
                elif duration >= 45:
                    movement_xp += 150
                elif duration >= 30:
                    movement_xp += 100
            elif data['activity_name'] == 'Mind and Body':
                metadata = data.get('metadata', '')

                # Default to empty string if metadata is not provided
                if metadata == 'Moment of Silence':
                    movement_xp += 20 * duration
                elif metadata == 'Meditation':
                    movement_xp += 100 * (duration // 10)
        return movement_xp

    def update_xp(self, workout_activity):
        user = workout_activity.user
        activity_date = workout_activity.start_datetime.date()
        user_xp, created_xp = Xp.objects.get_or_create(
            user=user,
            date=activity_date,
            defaults={
                'totalXpToday': workout_activity.xp,
                'totalXpAllTime': workout_activity.xp,
                'timeStamp': workout_activity.start_datetime
            }
        )
        if not created_xp:
            user_xp.totalXpToday += workout_activity.xp
            user_xp.totalXpAllTime += workout_activity.xp
            user_xp.save()

    def update_user_leagues(self, user, new_xp, xp_date):
        active_leagues = UserLeague.objects.filter(
            user=user,
            league_instance__is_active=True
        ).select_related('league_instance__company')

        for user_league in active_leagues:
            league_instance = user_league.league_instance
            league_start_date = league_instance.league_start

            user_timezone = ZoneInfo(user.timezone.key)
            xp_date_local = xp_date.replace(tzinfo=user_timezone)
            xp_date_utc = xp_date_local.astimezone(timezone.utc)

            if xp_date_utc >= league_start_date:
                if league_instance.company is not None:
                    user_league.xp_company += new_xp
                else:
                    user_league.xp_global += new_xp
                user_league.save()


class XpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Xp
        fields = '__all__'  # Adjust as necessary

class StreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = Streak
        fields = '__all__'  # Adjust as necessary


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']  # User and timestamp should not be set manually

    def validate_item_name(self, value):
        # Ensure the item_name is one of the predefined choices
        if value not in dict(Purchase.ITEM_CHOICES).keys():
            raise serializers.ValidationError("Invalid item choice.")
        return value

class PrizeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = Prize
        fields = ['id', 'name', 'description', 'value', 'quantity']


class DrawImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = DrawImage
        fields = ['image_link', 'title']


class DrawSerializer(serializers.ModelSerializer):
    prizes = PrizeSerializer(many=True)  # Add nested PrizeSerializer
    entry_count = serializers.SerializerMethodField()
    user_entry_count = serializers.SerializerMethodField()  # User-specific entry count
    images = DrawImageSerializer(many=True, read_only=True) # Nested DrawImageSerializer

    class Meta:
        model = Draw
        fields = ['id', 'draw_name', 'draw_type', 'draw_date', 'number_of_winners', 'is_active', 'entry_count','video', 'prizes','user_entry_count','images']
        read_only_fields = ['id', 'draw_name', 'draw_type', 'draw_date', 'is_active', 'entry_count', 'user_entry_count']

    def get_entry_count(self, obj):
        return obj.entries.count()  # Count the related DrawEntry objects

    # Number of entries for the authenticated user in this draw
    def get_user_entry_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.entries.filter(user=request.user).count()  # Count entries for the logged-in user
        return 0  # Return 0 if the user is not authenticated or has no entries


    def validate(self, data):
        """Validate the incoming data, checking for any read-only or unexpected fields."""
        self._validate_unexpected_fields(data)
        self._validate_read_only_fields(data)
        return data

    def _validate_unexpected_fields(self, data):
        unexpected_fields = set(data.keys()) - set(self.Meta.fields)
        if unexpected_fields:
            raise serializers.ValidationError({
                field: f"{field} is not a valid field." for field in unexpected_fields
            })

    def _validate_read_only_fields(self, data):
        for field in self.Meta.read_only_fields:
            if field in data:
                raise serializers.ValidationError({
                    f"{field}": f"{field} cannot be modified."
                })

    def update(self, instance, validated_data):
        # print("Incoming Request Data:", self.context['request'].data)
        # print("Validated Data:", validated_data)

        prizes_data = validated_data.pop('prizes', [])
        instance = super().update(instance, validated_data)  # Update the draw instance

        # Process and update the related prizes
        self._update_or_create_prizes(instance, prizes_data)

        return instance

    def _update_or_create_prizes(self, instance, prizes_data):
        """Update existing prizes or create new ones."""
        for prize_data in prizes_data:
            prize_id = prize_data.get('id')
            # print("Processing Prize ID:", prize_id)

            if prize_id:
                self._update_existing_prize(prize_id, prize_data)
            else:
                self._create_new_prize(instance, prize_data)

    def _update_existing_prize(self, prize_id, prize_data):
        """Update an existing prize if it exists."""
        try:
            prize = Prize.objects.get(id=prize_id)
            prize.name = prize_data.get('name', prize.name)
            prize.description = prize_data.get('description', prize.description)
            prize.save()
        except Prize.DoesNotExist:
            Prize.objects.create(**prize_data)

    def _create_new_prize(self, draw, prize_data):
        """Create a new prize if no ID is provided."""
        Prize.objects.create(draw=draw, **prize_data)
        print(f"Created New Prize: {prize_data}")


class DrawEntrySerializer(serializers.ModelSerializer):
    draw = serializers.PrimaryKeyRelatedField(queryset=Draw.objects.all())  # Use PrimaryKeyRelatedField
    class Meta:
        model = DrawEntry
        fields = ['user', 'draw', 'timestamp']


class DrawWinnerSerializer(serializers.ModelSerializer):
    draw = DrawSerializer()
    prize = PrizeSerializer()
    user = serializers.CharField(source='user.username')  # Display the user's name

    class Meta:
        model = DrawWinner
        fields = ['draw', 'user', 'prize', 'win_date']


class NotifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notif
        fields = ['id', 'user', 'notif_type', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']  # Optional: if you want these fields to be read-only

    def create(self, validated_data):
        # Get the user from the view context (request)
        user = self.context['request'].user

        # Ensure the user is included in validated_data
        validated_data['user'] = user

        return super().create(validated_data)

    def to_representation(self, instance):
        # Get the current user from the view context
        user = self.context['request'].user

        # Get the user's timezone
        user_timezone = user.timezone  # Assuming the 'timezone' field exists in the user model
        utc_time = instance.created_at  # Assuming `created_at` is a timezone-aware datetime

        # Convert the `created_at` to the user's local time
        user_local_time = utc_time.astimezone(user_timezone)

        # Create the serialized data
        representation = super().to_representation(instance)

        # Replace `created_at` with the converted local time
        representation['created_at'] = user_local_time.isoformat()  # Use ISO 8601 format for the datetime string

        return representation
