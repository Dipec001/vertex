from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company, Invitation, Membership
import random
import string
from allauth.socialaccount.models import SocialAccount
import logging
from rest_framework.validators import UniqueValidator
from django.db import transaction
from .tasks import send_invitation_email_task


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
        fields = ['email', 'invite_code', 'status', 'date_sent','invited_by']
        read_only_fields = ['invite_code', 'status', 'date_sent', 'invited_by']  # Mark these as read-only for creatio

    def create(self, validated_data):
        email = validated_data['email']
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
    class Meta:
        model = CustomUser
        fields = ['username', 'bio', 'profile_picture'] 



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
