from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company, Invitation
import random
import string
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

CustomUser = get_user_model()


class CompanyOwnerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)  # Explicitly defining email field
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

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        company_name = validated_data['company_name']
        domain = validated_data.get('domain', '')  # Get domain or set it to an empty string if not provided

        # Extract the email prefix to use as the username
        username = self.generate_unique_username(email)

        # Create the user and set `is_company_owner` to True
        user = CustomUser.objects.create_user(email=email, username=username, password=password, is_company_owner=True)

        # Set the username as the email prefix
        user.username = username
        user.save()

        # Create the company and associate it with the owner
        company = Company.objects.create(name=company_name, owner=user, domain=domain)

        return user, company


class NormalUserSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)  # Explicitly defining email field
    profile_picture = serializers.ImageField(required=False, allow_null=True)  # Optional profile picture field

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'username', 'profile_picture']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists.")
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists.")
        return data

    def create(self, validated_data):
        # Extract the profile picture if it exists
        profile_picture = validated_data.pop('profile_picture', None)
        
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data['username']
        )
         # If a profile picture was provided, assign it to the user
        if profile_picture:
            user.profile_picture = profile_picture
            user.save()

        return user


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
        
        # Check if the email already belongs to a member of the company
        existing_member = company.members.filter(email=email).exists()

        if existing_member:
            raise serializers.ValidationError({"error": f"{email} is already a member of {company.name}."})

        # Generate a unique invite code
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Prepare the email content
        subject = "You're Invited to Join Our Company"
        html_message = render_to_string('invitation_email.html', {
            'invite_code': invite_code,
            'company_name': company.name,
            'inviter_name': user.username,
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = email

        # Send the email
        # Send the email with error handling
        try:
            send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
        except TimeoutError:
            logger.error(f"TimeoutError while sending email to {email}.")
            raise serializers.ValidationError({"error": "Failed to send invitation email. Please try again later."})
        except BadHeaderError:
            logger.error(f"BadHeaderError while sending email to {email}.")
            raise serializers.ValidationError({"error": "Invalid header found."})
        except Exception as e:
            logger.error(f"An error occurred while sending email to {email}: {e}")
            raise serializers.ValidationError({"error": "An unexpected error occurred while sending the email."})

        # Create the invitation
        invitation = Invitation.objects.create(
            email=email,
            company=company,
            invite_code=invite_code,
            invited_by=self.context['request'].user  # The user sending the invitation
        )
        return invitation


class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        # Include all fields except the raw profile_picture and profile_picture_url
        fields = [
            'email', 
            'username', 
            'is_company_owner', 
            'streak', 
            'bio', 
            'date_joined', 
            'tickets', 
            'profile_picture_url'  # Custom field with logic
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