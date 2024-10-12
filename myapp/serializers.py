from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company, Invitation, Membership, WorkoutActivity, Xp, Streak, DailySteps
import random
import string
from allauth.socialaccount.models import SocialAccount
import logging
from rest_framework.validators import UniqueValidator
from django.db import transaction
from .tasks import send_invitation_email_task
from django.utils import timezone
from .timezone_converter import convert_to_utc
import pytz
from zoneinfo import ZoneInfo
from timezone_field.rest_framework import TimeZoneSerializerField


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
            'bio', 
            'date_joined', 
            'tickets', 
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

        # Get or create the daily steps record
        daily_steps, created = DailySteps.objects.get_or_create(
            user=user,
            date=date,
            defaults={'step_count': step_count, 'xp': step_count / 10}
        )

        # If the record is newly created
        if created:
            new_xp = step_count / 10  # Calculate XP for the new record
            daily_steps.xp = new_xp
        else:
            # If the record already exists, update it with new step count
            step_diff = step_count - daily_steps.step_count
            if step_diff > 0:  # Only award XP for additional steps
                new_xp = step_diff / 10
                daily_steps.step_count = step_count  # Update step count
                daily_steps.xp += new_xp  # Update XP
            else:
                new_xp = 0  # No XP to be awarded if no additional steps

        daily_steps.timestamp = timezone.now()  # Update timestamp
        daily_steps.save()
        
        # Update the user's XP record for today
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

    def create(self, validated_data):
        user = self.context['request'].user

        # Check for existing workout activities that conflict with the new one
        if (WorkoutActivity.objects.filter(
                user=user,
                start_datetime=validated_data['start_datetime'],
                end_datetime=validated_data['end_datetime']
            ).exists()):
            raise serializers.ValidationError("A workout with the same start and end times already exists.")

        # Convert times to UTC (optional depending on your timezone logic)
        # validated_data['start_datetime'] = convert_to_utc(user.timezone, validated_data['start_datetime'])
        # validated_data['end_datetime'] = convert_to_utc(user.timezone, validated_data['end_datetime'])

        # Calculate XP based on activity and details
        xp_earned = self.calculate_xp(validated_data)
        validated_data['xp'] = xp_earned

        # Save the activity record
        workout_activity = WorkoutActivity.objects.create(user=user, **validated_data)

        # Update XP and Streak
        self.update_xp(workout_activity)

        return workout_activity

    def calculate_xp(self, data):
        duration = data.get('duration', 0)
        activity_type = data.get('activity_type')
        movement_xp = 0

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

        elif activity_type == 'mindfulness':
            if data['activity_name'] == 'Yoga' and duration >= 30:
                movement_xp += 100
            elif data['activity_name'] == 'Moment of Silence':
                movement_xp += 20 * duration
            elif data['activity_name'] == 'Meditation':
                movement_xp += 100 * (duration // 10)

        return movement_xp

    def update_xp(self, workout_activity):

        user = workout_activity.user
        # Extract the date from the timestamp
        activity_date = workout_activity.start_datetime.date()  # or workout_activity.end_datetime.date()

        # Update or create an XP record for that user and the current day
        xp_record, created = Xp.objects.get_or_create(
            user=user,
            timeStamp__date=activity_date,  # Ensure one XP record per day
            defaults={
                'totalXpToday': workout_activity.xp,
                'totalXpAllTime': workout_activity.xp,
            }
        )

        # Update the XP fields
        xp_record.totalXpToday += workout_activity.xp
        xp_record.totalXpAllTime += workout_activity.xp
        xp_record.currentXpRemaining += workout_activity.xp
        xp_record.save()


class XpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Xp
        fields = '__all__'  # Adjust as necessary

class StreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = Streak
        fields = '__all__'  # Adjust as necessary
