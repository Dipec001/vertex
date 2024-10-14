from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company, Invitation, Membership, WorkoutActivity, Xp, Streak, DailySteps, Purchase
import random
import string
from allauth.socialaccount.models import SocialAccount
import logging
from rest_framework.validators import UniqueValidator
from django.db import transaction
from .tasks import send_invitation_email_task
from django.utils import timezone
from .timezone_converter import convert_to_utc, convert_from_utc
from timezone_field.rest_framework import TimeZoneSerializerField
from pytz import UTC
from datetime import datetime


logger = logging.getLogger(__name__)

CustomUser = get_user_model()

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
    streak = serializers.SerializerMethodField()  # Adding a method field for streak
    streak_savers = serializers.IntegerField(read_only=True)  # Include streak savers
    global_tickets = serializers.IntegerField(read_only=True)  # Include tickets
    company_tickets = serializers.IntegerField(read_only=True)  # Include tickets


    class Meta:
        model = CustomUser
        # Include all fields except the raw profile_picture and profile_picture_url
        fields = [
            'email', 
            'username',
            'first_name',
            'last_name',
            'is_company_owner', 
            'streak', 
            'streak_savers',
            'global_tickets',
            'company_tickets',
            'bio', 
            'date_joined', 
            'profile_picture_url',  # Custom field with logic
            'company',
        ]

    def get_profile_picture_url(self, obj):
        # If the user has an uploaded profile picture, return its URL
        if obj.profile_picture:
            return obj.profile_picture.url
        
        # If the user has provided an external profile picture URL, return it
        if obj.profile_picture_url:
            return obj.profile_picture_url
        
        # Fallback to a default image if neither is set
        # return '/static/images/default_avatar.png'

    def get_streak(self, obj):
        # Fetch the latest Streak record for the user
        latest_streak = obj.streak_records.order_by('-timeStamp').first()
        return latest_streak.currentStreak if latest_streak else 0  # Return 0 if no streak found


class UpdateProfileSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)  # Change to False if you want `zoneinfo` objects
    class Meta:
        model = CustomUser
        fields = ['username', 'bio', 'profile_picture', 'timezone'] 



class NormalUserSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    profile_picture = serializers.URLField(required=False, allow_null=True)
    invitation_id = serializers.IntegerField(required=True)  # Include invitation_id for validation
    password = serializers.CharField(write_only=True, required=False, allow_null=True)  # Make password optional
    login_type = serializers.ChoiceField(choices=CustomUser.LOGIN_TYPE_CHOICES, required=True)
    uid = serializers.CharField(required=False, allow_null=True)  # UID for social logins
    first_name = serializers.CharField(required=False, allow_null=True)
    last_name = serializers.CharField(required=False, allow_null=True)


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

        # Get UID and login type from session
        # request = self.context['request']
        # uid = request.session.get('uid')
        # login_type = request.session.get('login_type')

        # Create user based on login type
        if login_type in ['google', 'facebook', 'apple']:
            # social sign up
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
            
            # Clear session data after creating the account
            # del request.session['uid']
            # del request.session['login_type']
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
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation ID.")

        return user



class DailyStepsSerializer(serializers.ModelSerializer):
    xp = serializers.FloatField(read_only=True)  # XP is calculated and read-only
    
    class Meta:
        model = DailySteps
        fields = ['step_count', 'timestamp', 'date', 'xp']  # Include 'date' for validation
        extra_kwargs = {
            'timestamp': {'read_only': True},  # Set timestamp as read-only if needed
            'date': {'required': False}  # Make date optional
        }
    
    def validate_step_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Step count cannot be negative.")
        return value

    def validate_date(self, value):
        """Ensure the date is not in the future."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        step_count = validated_data.get('step_count')
        date = validated_data.get('date', timezone.now().date())  # Use today's date if not provided

        # Get or create the daily steps record (only one entry per day)
        daily_steps, created = DailySteps.objects.get_or_create(
            user=user,
            date=date,
            defaults={'step_count': step_count, 'xp': step_count / 10}
        )

        # Calculate new XP and update daily step count
        if created:
            # For the first entry, set the initial XP based on the step count
            new_xp = step_count / 10  # Calculate XP for the new record
            daily_steps.xp = new_xp
        else:
            # Calculate XP based on additional steps
            step_diff = step_count - daily_steps.step_count
            if step_diff > 0:  # Only award XP for additional steps
                new_xp = step_diff / 10
                daily_steps.step_count = step_count  # Update step count
                daily_steps.xp += new_xp  # Update XP
            else:
                new_xp = 0  # No XP to be awarded if no additional steps

        daily_steps.timestamp = timezone.now()  # Update timestamp
        daily_steps.save()

        # Update the user's XP record for today (in your XP model)
        user_xp, created_xp = Xp.objects.get_or_create(
            user=user,
            timeStamp__date=date,  # Ensure it's tied to today
            defaults={
                'totalXpToday': new_xp,
                'totalXpAllTime': new_xp,
                'currentXpRemaining': new_xp
            }
        )

        # Only update XP fields if the record already exists, or if new XP is added
        if not created_xp and new_xp > 0:
            user_xp.totalXpToday += new_xp
            user_xp.totalXpAllTime += new_xp
            user_xp.currentXpRemaining += new_xp
            user_xp.save()

        # Record the additional steps in the WorkoutActivity model (multiple entries per day)
        if new_xp > 0:  # Only create a new workout entry if there is additional XP
            WorkoutActivity.objects.create(
                user=user,
                activity_type="movement",
                activity_name="steps",
                xp=new_xp,  # Only the additional XP
                duration=0,  # No duration for step counts
                distance=0,
                average_heart_rate=0,
                start_datetime=timezone.now(),
                end_datetime=timezone.now(),
                metadata='{}',
                current_date=date,
                deviceType=None
            )

        return daily_steps


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
            'current_date',
            'deviceType',
        ]

    def validate(self, data):
        """
        Custom validation for start/end times.
        """

        # Get the converted datetime from the view
        start_datetime_utc = data.get('start_datetime')
        end_datetime_utc = data.get('end_datetime') 
        
        # Check for conversion failure/ Ensure both datetime values are provided
        if start_datetime_utc is None or end_datetime_utc is None:
            raise serializers.ValidationError("Invalid date format for start_datetime or end_datetime.")

        # Check if end_datetime is before start_datetime
        if data['end_datetime'] <= data['start_datetime']:
            raise serializers.ValidationError("End time must be after the start time.")


        return data

    def create(self, validated_data):
        user = self.context['request'].user

        # Check if `current_date` is provided, otherwise infer it from `start_datetime`
        if 'current_date' not in validated_data:
            validated_data['current_date'] = validated_data['start_datetime'].date()

        # Extract the date from the start_datetime to ensure conflict checking only happens for the same day
        start_date = validated_data['start_datetime'].date()
        end_date = validated_data['end_datetime'].date()


        # Check for existing workout activities on the same day only
        if (WorkoutActivity.objects.filter(
                user=user,
                start_datetime__date=start_date,
                end_datetime__date=end_date,
                start_datetime=validated_data['start_datetime'],
                end_datetime=validated_data['end_datetime']
            ).exists()):
            raise serializers.ValidationError("A workout with the same start and end times already exists for this day.")

        # Calculate XP based on activity and details
        xp_earned = self.calculate_xp(validated_data)
        validated_data['xp'] = xp_earned

        # Save the activity record
        workout_activity = WorkoutActivity.objects.create(user=user, **validated_data)

        # Update XP for the user
        self.update_xp(workout_activity)

        return workout_activity

    def calculate_xp(self, data):
        duration = data.get('duration', 0)
        activity_type = data.get('activity_type')
        movement_xp = 0

        # XP calculation logic for movement activities
        if activity_type == 'movement':
            if duration >= 30:
                movement_xp += 100
            if duration >= 45:
                movement_xp += 150
            if duration >= 60:
                movement_xp += 200

            avg_bpm = data.get('average_heart_rate', 0)
            if 100 <= avg_bpm < 120:
                movement_xp += 20
            elif 120 <= avg_bpm < 150:
                movement_xp += 40
            elif avg_bpm >= 150:
                movement_xp += 60

        # XP calculation logic for mindfulness activities
        elif activity_type == 'mindfulness':
            if data['activity_name'] == 'Yoga' and duration >= 30:
                movement_xp += 100
            elif data['activity_name'] == 'Mind and Body':
                if data['metadata'] == 'Moment of Silence':
                    movement_xp += 20 * duration
                elif data['metadata'] == 'Meditation':
                    movement_xp += 100 * (duration // 10)

        return movement_xp

    def update_xp(self, workout_activity):
        user = workout_activity.user
        # Extract the date from the timestamp
        activity_date = workout_activity.start_datetime.date()

        # Get start and end of day in UTC to avoid multiple objects issue
        start_of_day = timezone.datetime.combine(activity_date, timezone.datetime.min.time()).replace(tzinfo=UTC)
        end_of_day = timezone.datetime.combine(activity_date, timezone.datetime.max.time()).replace(tzinfo=UTC)

        # Update or create an XP record for that user and the current day
        user_xp, created_xp = Xp.objects.get_or_create(
            user=user,
            timeStamp__gte=start_of_day,
            timeStamp__lte=end_of_day,
            defaults={
                'totalXpToday': workout_activity.xp,
                'totalXpAllTime': workout_activity.xp,
                'currentXpRemaining': workout_activity.xp
            }
        )

        # Only update XP fields if the record already exists
        if not created_xp:
            user_xp.totalXpToday += workout_activity.xp

        # Retrieve the previous XP record (excluding the current day)
        previous_xp = Xp.objects.filter(user=user).exclude(timeStamp__date=activity_date).order_by('-timeStamp').first()

        if previous_xp:
            # If there is a previous record, use its values for all-time and remaining XP
            user_xp.totalXpAllTime = previous_xp.totalXpAllTime + workout_activity.xp
            user_xp.currentXpRemaining = previous_xp.currentXpRemaining + workout_activity.xp
        else:
            # If no previous record exists, use the current workout XP
            user_xp.totalXpAllTime += workout_activity.xp
            user_xp.currentXpRemaining += workout_activity.xp

        # Save the XP record
        user_xp.save()



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