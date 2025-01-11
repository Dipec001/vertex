from pprint import pprint
from typing import Literal
from rest_framework_simplejwt.views import TokenObtainPairView
import pandas as pd
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView, ListCreateAPIView, \
    RetrieveUpdateDestroyAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django_filters import rest_framework
from myapp.utils import send_user_notification, \
    get_last_day_and_first_day_of_this_month
from .invitation_service import send_invitation_in_bulk
from .stats_service import get_global_xp_for_stats_by_user, get_global_xp_for_stats, get_daily_steps_and_xp
from .filters import EmployeeFilterSet, CompanyFilterSet, InvitationFilterSet
from .serializers import (CompanyOwnerSignupSerializer, NormalUserSignupSerializer,
                          InvitationSerializer, UserProfileSerializer, UpdateProfileSerializer,
                          DailyStepsSerializer, WorkoutActivitySerializer, PurchaseSerializer,
                          DrawWinnerSerializer, DrawEntrySerializer, DrawSerializer, FeedSerializer,
                          NotifSerializer, EmployeeSerializer, CompanySerializer, InvitationAsEmployeeSerializer, FileUploadSerializer, BulkInvitationResultSerializer,
                          ManualDrawCreateSerializer, ManualPrizeCreateSerializer)
from .models import (CustomUser, Invitation, Company, Membership, DailySteps, Xp, WorkoutActivity,
                     Streak, Purchase, DrawWinner, DrawEntry, Draw, UserLeague, LeagueInstance, UserFollowing, Feed,
                     Clap, ActiveSession,
                     League, Gem, DrawImage, Notif, Prize)
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.urls import reverse
from .google_validate import validate_google_token
from .apple_validate import validate_apple_token
from .facebook_validate import validate_facebook_token
import requests
from allauth.socialaccount.models import SocialAccount
from django.db import transaction
from .s3_utils import save_image_to_s3
from django.utils import timezone
from django.db.models import Sum, F, Max, Avg, Count
from datetime import datetime, timedelta
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from rest_framework.throttling import UserRateThrottle
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils.timezone import localtime, now
from .tasks import upload_file_task, send_login_successful_email_task
import tempfile
import os
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
import logging
from .permissions import IsCompanyOwner, IsCompanyOwnerPK
from notifications.utils import send_followclap_notification
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from rest_framework.response import Response
from django_filters import rest_framework as filters

# Set up logging
logger = logging.getLogger(__name__)
# from notifications.utils import send_notification


class StreakRateThrottle(UserRateThrottle):
    rate = "5/min"  # 1 request per  mins


# Create your views here.
@login_required
def test_league_rankings(request):
    # Fetch the active league for the logged-in user
    user_league = (
        UserLeague.objects
        .filter(user=request.user, league_instance__is_active=True, league_instance__company__isnull=True)
        .select_related('league_instance', 'user')
        .first()
    )

    if not user_league:
        return render(request, 'global_league.html', {'error': 'No active league found for testing'})

    # Pass the league ID to the template
    league_id = user_league.league_instance.id
    return render(request, 'global_league.html', {'league_id': league_id})

@login_required
def test_streak_view(request):
    return render(request, 'test_streak.html', {'user_id': request.user.id})


@login_required
def test_gem_view(request):
    return render(request, 'test_gem.html', {'user_id': request.user.id})


@login_required
def test_feed_view(request):
    return render(request, 'test_feed.html', {'user_id': request.user.id})


@login_required
def test_draw_view(request):
    return render(request, 'test_draw.html', {'user_id': request.user.id})


@login_required
def test_noti_view(request):
    return render(request, 'test_noti.html')


def test_error(request):
    raise Exception("This is a test error for email notification")


class ValidateEmailPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        # Ensure email and password are provided
        if not email or not password or not confirm_password:
            return Response({"error": "Email, password, and confirm password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Check if passwords match
        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email is already registered
        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # If everything is valid, return success
        return Response({
            "success": "Email and password are valid.",
            "login_type": "Email and password"
        }, status=status.HTTP_200_OK)


class ValidateCompanyAssociationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        company_email_or_code = request.data.get('company_email_or_code').lower()

        # Ensure company email or invite code is provided
        if not company_email_or_code:
            return Response({"error": "Company email or invite code is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if company email or invite code is valid (either email or code can be used)
        try:
            if '@' in company_email_or_code:
                invitation = Invitation.objects.get(email=company_email_or_code, status='pending')
            else:
                invitation = Invitation.objects.get(invite_code=company_email_or_code, status='pending')
        except Invitation.DoesNotExist:
            return Response({"error": "Invalid company email or invite code."}, status=status.HTTP_400_BAD_REQUEST)

        # If everything is valid, return success
        # Return success and the associated information
        return Response({
            "success": "Valid company email or invite code.",
            "invitation_id": invitation.id,
            "email": invitation.email  # Return the invitation email if needed
        }, status=status.HTTP_200_OK)


class VerifyUsernameView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')

        if not username:
            return Response({"error": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert the username to lowercase for case-insensitive comparison
        if CustomUser.objects.filter(username__iexact=username.lower()).exists():
            return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Username is available."}, status=status.HTTP_200_OK)


class NormalUserSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NormalUserSignupSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyOwnerSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CompanyOwnerSignupSerializer(data=request.data)

        # Validate the data
        if serializer.is_valid():
            user, company = serializer.save()

            return Response({
                'success': True,
                'message': 'Company and owner account created successfully.',
                'user': {
                    'email': user.email,
                    'username': user.username,  # Include the username (email prefix)
                    'company_name': company.name,
                    'domain': company.domain
                }
            }, status=status.HTTP_201_CREATED)

        # Return errors if any
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Generate reset token
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Generate reset URL
        reset_url = f"{request.build_absolute_uri('/')[:-1]}{reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"

        # Send email with reset link
        send_mail(
            subject="Password Reset Request",
            message=f"Click the link below to reset your password:\n{reset_url}",
            from_email='dpecchukwu@gmail.com',
            recipient_list=[email],
        )

        return Response({"success": "Password reset link sent."}, status=status.HTTP_200_OK)


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    token_generator = default_token_generator

    if user is not None and token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if (new_password or confirm_password) is None:
                messages.error(request, 'Password and confirm password is required')
                return render(request, 'password_reset_form.html')

            if new_password == confirm_password:
                user.password = make_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully. You can log back in on the app')
                # return redirect('login')  # Redirect to the login page after reset
            else:
                messages.error(request, 'Passwords do not match.')
        return render(request, 'password_reset_confirm.html', {'validlink': True})
    else:
        messages.error(request, 'The reset link is invalid or has expired.')
        return render(request, 'password_reset_confirm.html', {'validlink': False})

class SendInvitationViewInBulk(APIView):
    "This endpoint is used to send an invitation by the company owner or HR and also get list of invitations sent in bulk"
    permission_classes = [IsAuthenticated]
    serializer_class = FileUploadSerializer

    def post(self, request, company_id):
        # Fetch the company based on the ID
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch the user's membership in the company
        try:
            membership = Membership.objects.get(user=request.user, company=company)
        except Membership.DoesNotExist:
            return Response({"error": "You are not a member of this company."}, status=status.HTTP_403_FORBIDDEN)

        # Check if the user is either the company owner or an HR manager
        if membership.role not in ['owner', 'HR']:
            return Response({"error": "You do not have permission to send invitations."}, status=status.HTTP_403_FORBIDDEN)

        file_serializer = self.serializer_class(data=request.data)
        if not file_serializer.is_valid():
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        file_extension = uploaded_file.name.split('.')[-1].lower()

        try:
            # Read file using pandas for both CSV and Excel
            if file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
            elif file_extension in ['xls', 'xlsx']:
                df = pd.read_excel(uploaded_file)
            else:
                return Response(
                    {'error': 'Unsupported file format. Please upload CSV or Excel file.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convert DataFrame to list of dictionaries
            invited_persons = df.to_dict('records')

            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email']
            if not all(field in df.columns for field in required_fields):
                return Response(
                    {'error': f'File must contain the following columns: {", ".join(required_fields)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Clean and validate data
            validated_persons = []
            failed_invitations = []

            for person in invited_persons:
                # Check for missing or empty values
                if (all(field in person for field in required_fields) and
                        all(isinstance(person.get(field), str) and person.get(field).strip() for field in
                            required_fields)):
                    validated_persons.append({
                        'email': person['email'].strip(),
                        'first_name': person['first_name'].strip(),
                        'last_name': person['last_name'].strip()
                    })
                else:
                    failed_invitations.append({
                        'data': person,
                        'error': 'Missing or invalid required fields'
                    })

            created_invitations = send_invitation_in_bulk(
                invited_persons=validated_persons,
                inviter_user=request.user,
                inviter_company=company
            )

            result = {
                'success_count': len(created_invitations),
                'failed_invitations': failed_invitations
            }

            result_serializer = BulkInvitationResultSerializer(data=result)
            result_serializer.is_valid()
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

class SendInvitationView(APIView):
    "This endpoint is used to send an invitation by the company owner or HR and also get list of invitations sent"

    permission_classes = [IsAuthenticated]

    def post(self, request, company_id):
        # Fetch the company based on the ID
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch the user's membership in the company
        try:
            membership = Membership.objects.get(user=request.user, company=company)
        except Membership.DoesNotExist:
            return Response({"error": "You are not a member of this company."}, status=status.HTTP_403_FORBIDDEN)

        # Check if the user is either the company owner or an HR manager
        if membership.role not in ['owner', 'HR']:
            return Response({"error": "You do not have permission to send invitations."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = InvitationSerializer(data=request.data, context={'request': request, 'company': company})

        if serializer.is_valid():
            serializer.save()
            return Response({"success": "Invitation sent successfully."}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, company_id):
        company = Company.objects.get(id=company_id)

        # Fetch the company
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch the user's membership in the company
        try:
            membership = Membership.objects.get(user=request.user, company=company)
        except Membership.DoesNotExist:
            return Response({"error": "You are not a member of this company."}, status=status.HTTP_403_FORBIDDEN)

        # Only allow the company owner to view all invitations
        if membership.role not in ['owner', 'HR']:
            return Response({"error": "You do not have permission to view these invitations."},
                            status=status.HTTP_403_FORBIDDEN)

        # Fetch all invitations for the company
        invitations = Invitation.objects.filter(company=company)
        serializer = InvitationSerializer(invitations, many=True, context={'request': request, 'company': company})

        return Response(serializer.data, status=status.HTTP_200_OK)


class GoogleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        google_token = request.data.get('id_token')

        if not google_token:
            return Response({'error': 'Google token is required'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_token = validate_google_token(google_token)
        if not decoded_token:
            return Response({'error': 'Invalid Google ID token'}, status=status.HTTP_400_BAD_REQUEST)

        print(decoded_token)

        # Get Google's unique user ID (sub)
        google_uid = decoded_token.get('sub')
        if not google_uid:
            return Response({'error': 'Invalid token format'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the user's email
        email = decoded_token.get('email')
        if not email:
            return Response({'error': 'User does not have an email address'}, status=status.HTTP_400_BAD_REQUEST)

        picture = decoded_token.get('picture', '')
        first_name = decoded_token.get('given_name')
        last_name = decoded_token.get('family_name')

        # Check if the user already exists based on Google UID
        try:
            social_account = SocialAccount.objects.get(uid=google_uid, provider__iexact='google')
            user = social_account.user

            # User exists, return access and refresh tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "is_new_user": False,
                "message": "User logged in successfully."
            }, status=status.HTTP_200_OK)

        except SocialAccount.DoesNotExist:
            # If user doesn't exist, handle it accordingly
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user:
                return Response({
                    'error': 'User with this email already exists',
                    'suggestion': 'Please log in with this email or use a different method to sign up.',
                }, status=status.HTTP_400_BAD_REQUEST)

            # No SocialAccount exists, temporarily store Google UID and email for future use
            # request.session['uid'] = google_uid
            # request.session['login_type'] = 'google'

            # No existing user found with this Google UID or email
            return Response({
                "is_new_user": True,
                "message": "New user detected. Please verify your invite code.",
                "google_uid": google_uid,
                "email": email,  # Email is always provided by Google
                "login_type": "google",
                "picture": picture,
                "first_name": first_name,
                "last_name": last_name
            }, status=status.HTTP_200_OK)


class AppleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Step 1: Validate the Apple ID token
        apple_token = request.data.get('id_token')
        if not apple_token:
            return Response({'error': 'Apple token is required'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_token = validate_apple_token(apple_token)
        if not decoded_token:
            return Response({'error': 'Invalid Apple ID token'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Extract relevant information from token
        apple_id = decoded_token.get('sub')
        email = decoded_token.get('email')  # ONly returned on first login
        # Extract the name from the decoded token if it's the first sign-in
        name_info = decoded_token.get('name', {})
        first_name = name_info.get('firstName')
        last_name = name_info.get('lastName')

        if not apple_id:
            return Response({'error': 'Apple ID not found in token'}, status=status.HTTP_400_BAD_REQUEST)

        # if not email:
        #     return Response({'error': 'Email not found in token'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 3: Check if the user already exists with SocialAccount
            social_account = SocialAccount.objects.get(uid=apple_id, provider='apple')
            user = social_account.user

            # Step 4: Existing user, return access and refresh tokens
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "is_new_user": False,
                    "message": "User logged in successfully."
                }, status=status.HTTP_200_OK)

        except SocialAccount.DoesNotExist:
            # This is a new user, handle first-time login
            # if email is None:
            #     return Response({'error': 'Email is required on first sign-in'}, status=status.HTTP_400_BAD_REQUEST)

            # Step 5: New User Detected, no account created yet
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user:
                return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)

            # Step 6: Indicate new user, prompt for further steps like invite code verification
            return Response({
                "is_new_user": True,
                "message": "New user detected. Please verify your invite code.",
                "email": email,
                "apple_id": apple_id,
                "login_type": "apple",
                "first_name": first_name,
                "last_name": last_name
            }, status=status.HTTP_200_OK)


class FacebookSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        facebook_token = request.data.get('access_token')

        if not facebook_token:
            return Response({'error': 'Facebook access token is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Facebook token
        try:
            user_id = validate_facebook_token(facebook_token)  # Assuming this checks the validity of the token
        except ValueError:
            return Response({'error': 'Invalid Facebook access token'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify Facebook token and get user info
        user_info_url = f'https://graph.facebook.com/me?access_token={facebook_token}&fields=id,name,email,picture'
        response = requests.get(user_info_url)

        if response.status_code != 200:
            return Response({'error': 'Failed to retrieve user information from Facebook'},
                            status=status.HTTP_400_BAD_REQUEST)

        user_info = response.json()
        facebook_uid = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture', {}).get('data', {}).get('url', '')

        if not facebook_uid:
            return Response({'error': 'Failed to retrieve user ID from Facebook'}, status=status.HTTP_400_BAD_REQUEST)

        # Split the name into first and last names
        first_name = name.split(' ')[0]
        last_name = ' '.join(name.split(' ')[1:])

        # Check if a social account or user already exists
        try:
            social_account = SocialAccount.objects.get(uid=facebook_uid, provider='facebook')
            user = social_account.user

            # User exists, return access and refresh tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "is_new_user": False,
                "message": "User logged in successfully."
            }, status=status.HTTP_200_OK)

        except SocialAccount.DoesNotExist:
            # If user doesn't exist, check for existing user by email
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user:
                return Response({
                    'error': 'User with this email already exists',
                    'suggestion': 'Please log in with this email or use a different method to sign up.',
                }, status=status.HTTP_400_BAD_REQUEST)

            # Return user details for new user sign-up
            return Response({
                "is_new_user": True,
                "message": "User validated successfully.",
                "uid": facebook_uid,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "profile_picture": picture
            }, status=status.HTTP_200_OK)


class PublicUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        user = get_object_or_404(CustomUser, id=id)
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # def put(self, request):
    #     from django.core.files.storage import default_storage
    #     print(f"Using storage backend: {default_storage.__class__}")

    #     user = request.user
    #     serializer = UpdateProfileSerializer(user, data=request.data, partial=True)

    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response({"success": "Profile updated successfully"}, status=status.HTTP_200_OK)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def put(self, request):
        logger.info(f"Incoming request data: {request.data}")
        logger.info(f"User making the request: {request.user}")

        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            profile_picture = request.FILES.get('profile_picture')
            if profile_picture:
                # Save image to S3 directly
                s3_object_key = save_image_to_s3(profile_picture, 'profile_pictures')

                if s3_object_key:
                    serializer.save(profile_picture=s3_object_key)
                else:
                    return Response({"error": "Failed to upload profile picture"},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                serializer.save()  # Save without updating the profile picture

            logger.info("Profile updated successfully.")
            return Response({"success": "Profile updated successfully"}, status=status.HTTP_200_OK)

        logger.error("Serializer errors:")
        logger.error(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user

        # Prevent company owners from deleting their account without transferring ownership
        if user.is_company_owner:  # Check if the user owns a company
            return Response(
                {"error": "You cannot delete your account while owning a company. Please transfer ownership first."},
                status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Revert invitation status to "pending" if it was accepted
        try:
            invitation = Invitation.objects.get(email=user.email, status="accepted")
            invitation.status = "pending"
            invitation.save()
        except Invitation.DoesNotExist:
            pass  # No invitation found, or it's still pending; nothing to do here

        # Step 2: Delete any associated social accounts (e.g., from django-allauth or custom social accounts)
        user.socialaccount_set.all().delete()

        # Step 3: Delete the user and all related records
        user.delete()

        return Response({"success": "Profile deleted successfully"}, status=status.HTTP_200_OK)


class TransferOwnershipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_owner_email = request.data.get('new_owner_email')

        # Check if the current user is indeed the owner
        try:
            company = Company.objects.get(owner=user)
        except Company.DoesNotExist:
            return Response({"error": "You are not the owner of any company."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the new owner exists
        try:
            new_owner = CustomUser.objects.get(email=new_owner_email)
        except CustomUser.DoesNotExist:
            return Response({"error": "New owner email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        # Begin transaction block to ensure atomicity
        with transaction.atomic():
            # Update the company owner
            company.owner = new_owner
            company.save()

            # Update the roles in the Membership model
            try:
                # Update the old owner's role to employee
                old_owner_membership = Membership.objects.get(user=user, company=company)
                old_owner_membership.role = 'employee'
                old_owner_membership.save()

                # Update the new owner's role to owner
                new_owner_membership, created = Membership.objects.get_or_create(user=new_owner, company=company)
                new_owner_membership.role = 'owner'
                new_owner_membership.save()

            except Membership.DoesNotExist:
                return Response({"error": "Membership not found for either user."}, status=status.HTTP_400_BAD_REQUEST)

            # Update ownership fields in CustomUser
            new_owner.is_company_owner = True
            new_owner.save()
            user.is_company_owner = False
            user.save()

            # # Optionally update invitations invited by the old owner to the new owner
            # # (This depends on whether you want to keep the historical invitation info)
            Invitation.objects.filter(invited_by=user, company=company).update(invited_by=new_owner)

        return Response({"success": "Company ownership transferred successfully."}, status=status.HTTP_200_OK)


class DailyStepsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', datetime.now().date())

        if not start_date:
            return Response({"error": "Please provide a start date."}, status=400)

        # Query steps and XP in the date range for the user, aggregate by date
        steps_in_range = DailySteps.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).values('date', 'timestamp').annotate(
            total_steps=Sum('step_count'),
            total_xp=Sum('xp')
        ).order_by('date')

        # Prepare the data to include both steps and XP for each day
        steps_data = []
        for step in steps_in_range:
            steps_data.append({
                'date': step['date'],
                'timestamp': step['timestamp'],
                'total_steps': step['total_steps'],
                'total_xp': int(step['total_xp'])
            })

        # Query total steps for the user across all time
        total_steps_count = DailySteps.objects.filter(user=request.user).aggregate(total_steps=Sum('step_count'))[
                                'total_steps'] or 0

        return Response({
            'steps_per_day': steps_data,
            'total_steps': total_steps_count
        })

    def post(self, request, *args, **kwargs):
        # Instantiate the serializer with the request data and user context
        serializer = DailyStepsSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # Save the serializer, which handles step count and XP logic
            daily_steps = serializer.save()

            # Retrieve the XP for the specified date
            date = daily_steps.date
            user_xp = Xp.objects.filter(user=request.user, date=date).first()

            # Calculate total XP across all records for the user
            total_xp_all_time = Xp.objects.filter(user=request.user).aggregate(Sum('totalXpToday'))[
                                    'totalXpToday__sum'] or 0

            # Prepare the response, handle the case where no XP record exists yet
            xp_data = {
                'totalXpToday': round(user_xp.totalXpToday, 1) if user_xp else 0,
                'totalXpAllTime': round(total_xp_all_time, 1),
            }

            return Response({
                'data': serializer.data,  # Serialized daily steps data
                'xp': xp_data,  # XP data for the current day
                'message': 'Update successful'
            }, status=status.HTTP_201_CREATED)
        # If the serializer is not valid, return the validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkoutActivityView(APIView):
    def get(self, request):
        user = request.user
        activities = WorkoutActivity.objects.filter(user=user)
        serializer = WorkoutActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = WorkoutActivitySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class StreakRecordsView(APIView):
#     throttle_classes = [StreakRateThrottle]
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         start_date = request.query_params.get('start_date')
#         end_date = request.query_params.get('end_date', timezone.now().date())

#         if not start_date:
#             return Response({"error": "Please provide a start date."}, status=400)

#         # Query streak records in the date range for the user
#         streak_in_range = Streak.objects.filter(
#             user=user,
#             timeStamp__date__range=[start_date, end_date]
#         ).values('timeStamp__date').annotate(current_streak=Sum('currentStreak')).order_by('timeStamp__date')

#         # Prepare the data
#         streak_data = [{'date': streak['timeStamp__date'], 'current_streak': streak['current_streak']} for streak in streak_in_range]

#         current_streak = user.streak

#         return Response({
#             'streak_per_day': streak_data,
#             'overall_current_streak': current_streak
#         })


class StreakRecordsView(APIView):
    """
    This view returns the streak records for the authenticated user over a specified date range.

    The response includes:
    - streak_per_day: A list of streak records per day within the specified date range.
    - overall_current_streak: The user's current streak value.

    The user's local time is used to determine the dates for querying streak records.
    """
    # throttle_classes = [StreakRateThrottle]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_tz = user.timezone

        # Get start and end dates from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', localtime(now(), user_tz).date())

        if not start_date:
            return Response({"error": "Please provide a start date."}, status=400)

        # Convert dates to user timezone
        today_date = localtime(now(), user_tz).date()

        # Query streak records in the user's local date range
        streak_in_range = Streak.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).values('date').annotate(current_streak=Sum('currentStreak')).order_by('date')

        # Prepare streak data for each day
        streak_data = [{'date': streak['date'], 'current_streak': streak['current_streak']} for streak in
                       streak_in_range]

        # Check if today's streak exists
        today_streak = next((entry['current_streak'] for entry in streak_data if entry['date'] == today_date), None)

        # Add today's streak dynamically if not found
        if today_streak is None:
            today_streak = 0
            streak_data.append({'date': today_date, 'current_streak': today_streak})

        # Current streak value for overall
        current_streak = user.streak

        return Response({
            'streak_per_day': streak_data,
            'overall_current_streak': current_streak,
        })


class XpRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Parse start_date and end_date from query parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        # Check if start_date is provided
        if not start_date_str:
            return Response({"error": "Please provide a start date."}, status=400)

        # Parse the dates
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str) if end_date_str else timezone.now().date()

        if not start_date:
            return Response({"error": "Invalid start date format."}, status=400)
        if not end_date:
            return Response({"error": "Invalid end date format."}, status=400)

        # Query XP records in the date range for the user
        xp_in_range = Xp.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).values('date').annotate(total_xp=Sum('totalXpToday')).order_by('date')

        xp_data = []

        # Loop over each day and fetch movement and mindfulness XP for that day
        for xp in xp_in_range:
            current_date = xp['date']

            # Fetch movement XP from WorkoutActivity
            movement_xp_workout = WorkoutActivity.objects.filter(
                user=request.user,
                start_datetime__date=current_date, # Filter based on start_datetime date
                activity_type="movement"
            ).aggregate(movement_xp=Sum('xp'))['movement_xp'] or 0

            # Fetch movement XP from DailySteps
            movement_xp_steps = DailySteps.objects.filter(
                user=request.user,
                date=current_date
            ).aggregate(steps_xp=Sum('xp'))['steps_xp'] or 0

            # Total movement XP for the day
            total_movement_xp = movement_xp_workout + movement_xp_steps

            # Fetch mindfulness XP for the current date
            mindfulness_xp = WorkoutActivity.objects.filter(
                user=request.user,
                start_datetime__date=current_date,  # Filter based on start_datetime date
                activity_type="mindfulness"
            ).aggregate(mindfulness_xp=Sum('xp'))['mindfulness_xp'] or 0

            # Append data for the current date
            xp_data.append({
                'date': current_date,
                'total_xp': round(xp['total_xp'], 1),
                'movement_xp': total_movement_xp,
                'mindfulness_xp': mindfulness_xp
            })

        # Fetch the actual total XP gained (across all time)
        total_xp_gained = Xp.objects.filter(user=request.user).aggregate(total_xp=Sum('totalXpToday'))['total_xp'] or 0

        # Return response with the breakdown per day and total XP gained
        return Response({
            'xp_per_day': xp_data,
            'total_xp_gained': total_xp_gained  # Sum of all XP across all time
        })


class ConvertGemView(APIView):
    permission_classes = [IsAuthenticated]

    # Define conversion rates
    GEM_COSTS = {
        'streak_saver': 2,
        'ticket_global': 1,
        'ticket_company': 1,
    }

    def post(self, request):
        user = request.user
        item_type = request.data.get('item_type')
        quantity = request.data.get('quantity', 1)  # Default quantity to 1 if not provided
        company_draw_id = request.data.get('company_draw_id')  # ID of the company draw to enter

        # Validate item_type and quantity
        if item_type not in self.GEM_COSTS:
            return Response({"error": "Invalid item type"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(quantity, int) or quantity <= 0:
            return Response({"error": "Quantity must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)

        gem_cost_per_item = self.GEM_COSTS[item_type]
        total_gem_cost = gem_cost_per_item * quantity

        total_available_gems = user.get_gem_count()
        print(total_available_gems)

        # Check if the user has enough available gems
        if total_available_gems < total_gem_cost:
            return Response({
                "error": f"Not enough gems. You need {total_gem_cost} gems for {quantity} {item_type}(s)."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Deduct the total gem cost
            user.gems_spent += total_gem_cost
            print('user_spent gems', user.gems_spent)

            # Update the user's tickets or streak savers
            if item_type == 'streak_saver':
                if user.streak_savers + quantity > 3:  # Check the total after adding the quantity
                    return Response({"error": "You can own 3 streak savers at most."},
                                    status=status.HTTP_400_BAD_REQUEST)

                user.streak_savers += quantity  # Properly increment the streak savers count

                # Create notification for receiving streak savers
                notif_type = "purchase_streaksaver"
                content = f"You converted {total_gem_cost} gems into {quantity} streak savers."


            elif item_type == 'ticket_global':

                # Ensure there is an active global draw whose end date has not passed
                global_draw = Draw.objects.filter(is_active=True, draw_type='global', draw_date__gt=now()).first()
                if not global_draw:
                    return Response({"error": "No active global draw available or unauthorised."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Add entries to the global draw
                entries = [DrawEntry(user=user, draw=global_draw) for _ in range(quantity)]
                DrawEntry.objects.bulk_create(entries)

                # Create notification for purchasing global draw tickets
                notif_type = "purchase_globaldraw"
                content = f"You converted {total_gem_cost} gems into {quantity} global draw tickets."

            elif item_type == 'ticket_company':
                if company_draw_id is None:
                    return Response({"error": "Company draw ID is required."}, status=status.HTTP_400_BAD_REQUEST)

                # Validate the company draw ID and check if there's an active company draw for the user's company
                try:
                    company_draw = Draw.objects.get(pk=company_draw_id, company__membership__user=user, is_active=True,
                                                    draw_date__gt=now())
                except Draw.DoesNotExist:
                    return Response(
                        {"error": "No active company draw available for the specified ID or not authorized."},
                        status=status.HTTP_404_NOT_FOUND)

                # Add entries to the specified company draw
                entries = [DrawEntry(user=user, draw=company_draw) for _ in range(quantity)]
                DrawEntry.objects.bulk_create(entries)

                # Create notification for purchasing company draw tickets
                notif_type = "purchase_companydraw"
                content = f"You converted {total_gem_cost} gems into {quantity} company draw tickets."

            user.save(update_fields=['gems_spent', 'streak_savers'])

            # Record the purchase
            purchase_data = {
                'item_name': item_type,
                'gem_used': total_gem_cost,
                'quantity': quantity
            }
            purchase_serializer = PurchaseSerializer(data=purchase_data)

            if purchase_serializer.is_valid():
                purchase_serializer.save(user=user)  # Save the purchase with the user
                # Create the notification
                notif_data = {
                    'user': user.id,
                    'notif_type': notif_type,  # Or any type you want
                    'content': content
                }
                notification_serializer = NotifSerializer(data=notif_data, context={'request': request})
                if notification_serializer.is_valid():
                    notification = notification_serializer.save()  # Save the notification

                    # Send WebSocket notification using the helper function
                    send_user_notification(user, notification)
                else:
                    return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(purchase_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Broadcast the updated gem count
            self.broadcast_gem_update(user)

        return Response({
            "message": f"You have successfully converted {total_gem_cost} gems for {quantity} {item_type}(s).",
            "remaining_gem": total_available_gems - total_gem_cost
        }, status=status.HTTP_200_OK)

    def broadcast_gem_update(self, user):
        new_gem_count = user.get_gem_count()  # Use the `get_gem_count` method to get the total gems
        print('new gem count', new_gem_count)

        # Calculate the remaining XP gems the user can earn today
        user_timezone = user.timezone
        user_local_time = datetime.now().astimezone(user_timezone)
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


class PurchaseHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Fetch user's purchase history
        purchases = Purchase.objects.filter(user=user)

        # Serialize the purchase data
        serializer = PurchaseSerializer(purchases, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class DrawHistoryAndWinnersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Draws user participated in
        participated_draws = DrawEntry.objects.filter(user=user).select_related('draw')

        # Draws user won
        won_draws = DrawWinner.objects.filter(user=user).select_related('draw', 'prize')

        response_data = {
            'participated_draws': DrawEntrySerializer(participated_draws, many=True).data,
            'won_draws': DrawWinnerSerializer(won_draws, many=True).data,
        }

        return Response(response_data)


class GetAllGlobalView(APIView):
    """
    Returns all active global draws.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Filter only active draws with draw_type as 'global'
        draws = Draw.objects.filter(is_active=True, draw_type='global')
        print(draws)

        # Serialize the draws
        serialized_draws = DrawSerializer(draws, many=True, context={'request': request}).data

        # Add user's ticket IDs (draw entries) to each draw
        for draw_data in serialized_draws:
            draw_id = draw_data['id']
            user_entries = DrawEntry.objects.filter(draw_id=draw_id, user=request.user).values_list('id', flat=True)
            draw_data['user_ticket_ids'] = list(user_entries)

        return Response(serialized_draws, status=status.HTTP_200_OK)


class GlobalDrawEditView(APIView):
    """
    View for editing global draws.
    Any user can view draw details, but only admin users can edit.
    """

    def get_object(self, pk):
        try:
            return Draw.objects.get(pk=pk, draw_type='global', is_active=True)  # Adjust based on your draw type logic
        except Draw.DoesNotExist:
            return None

    def get(self, request, pk):
        # Allow all users to view the draw details
        draw = self.get_object(pk)
        print(draw)
        if draw is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DrawSerializer(draw, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        # Only allow admin users to edit the draw details
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."},
                            status=status.HTTP_403_FORBIDDEN)

        draw = self.get_object(pk)
        if draw is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DrawSerializer(draw, data=request.data, partial=True)  # Enable partial updates
        if serializer.is_valid():
            video = request.FILES.get('video')
            if video:
                if video:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.name)[1]) as temp_file:
                        temp_file.write(video.read())
                        temp_file_path = temp_file.name

                    upload_file_task.delay(temp_file_path, 'draw_videos', 'video', draw_id=draw.id)

                    serializer.save(video='uploading')
            else:
                serializer.save()  # Save without updating the profile picture

            # Handle image uploads
            images = request.FILES.getlist('images')
            for image in images:
                title = request.POST.get('title', 'Default Title')
                s3_object_key = save_image_to_s3(image, 'draw_images')
                if s3_object_key:
                    image_link = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_object_key}"
                    DrawImage.objects.create(draw=draw, image_link=image_link, title=title)

            return Response({"success": "Draw updated initiated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyDrawEditView(APIView):
    def get(self, request, pk):
        try:
            # Only get the draw if the user is either the owner or HR manager
            draw = Draw.objects.get(
                pk=pk,
                company__membership__user=self.request.user,
            )
            serializer = DrawSerializer(draw, context={'request': request})
            return Response(serializer.data)
        except Draw.DoesNotExist:
            raise PermissionDenied("You do not have permission to access or manage this draw.")

    def put(self, request, pk):
        try:
            # Ensure only owners and HR managers can modify the draw
            draw = Draw.objects.get(
                pk=pk,
                company__membership__user=self.request.user,
                company__membership__role__in=['owner', 'HR']
            )
            if request.data == {}:
                return Response({'detail': 'No data passed'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = DrawSerializer(draw, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                # Use the custom update method here
                serializer.update(draw, serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Draw.DoesNotExist:
            raise PermissionDenied("You do not have permission to access or manage this draw.")


class CompanyListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySerializer
    filter_backends = [rest_framework.DjangoFilterBackend]
    filterset_class = CompanyFilterSet

    def get_queryset(self):
        return Company.objects.all().prefetch_related("ticket_set").order_by("id").annotate(
            total_employees=Count('membership'))


class CompanyDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsCompanyOwnerPK | permissions.IsAdminUser]
    serializer_class = CompanySerializer

    def get_queryset(self):
        return Company.objects.all().prefetch_related("ticket_set").annotate(total_employees=Count('membership'))


class CompanyDrawListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch the user's single membership to get their company
            membership = Membership.objects.get(user=request.user)

            # Get the company from the membership
            user_company = membership.company

            # Query all active draws for the user's company that are yet to happen
            draws = Draw.objects.filter(
                company=user_company,
                is_active=True,
                # Uncomment the line below to only fetch future draws
                # draw_date__gte=timezone.now()
            )

            # Serialize the draws
            serialized_draws = DrawSerializer(draws, many=True, context={'request': request}).data

            # Add user's ticket IDs (draw entries) to each draw
            for draw_data in serialized_draws:
                draw_id = draw_data['id']
                user_entries = DrawEntry.objects.filter(draw_id=draw_id, user=request.user).values_list('id', flat=True)
                draw_data['user_ticket_ids'] = list(user_entries)

            return Response(serialized_draws, status=status.HTTP_200_OK)

        except Membership.DoesNotExist:
            return Response({"error": "User does not belong to any company."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GlobalActiveLeagueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        user = request.user

        # Get the user's active global league instance
        user_league = (
            UserLeague.objects
            .filter(user=user, league_instance__is_active=True, league_instance__company__isnull=True)
            .select_related('league_instance', 'user')
            .first()
        )

        if not user_league:
            return Response({"error": "No active global league found for the user"}, status=404)

        league_instance = user_league.league_instance
        rankings = UserLeague.objects.filter(league_instance=league_instance).select_related('user').order_by(
            '-xp_global', '-user__streak', 'id')

        total_users = rankings.count()
        promotion_threshold = int(total_users * 0.30)  # Top 10%
        demotion_threshold = int(total_users * 0.80)  # Bottom 10%

        # Check if the league is the highest or lowest
        is_highest_league = league_instance.league.order == 10
        is_lowest_league = league_instance.league.order == 1

        rankings_data = []
        for index, ul in enumerate(rankings, start=1):
            if is_highest_league:
                # Highest league: users can only be retained or demoted
                if index <= demotion_threshold:
                    advancement = "Retained"
                    gems_obtained = 10
                else:
                    advancement = "Demoted"
                    gems_obtained = 0  # No gems for demoted users
            elif is_lowest_league:
                # Lowest league: users can be promoted based on ranking (top 30%)
                if index <= promotion_threshold:
                    advancement = "Promoted"
                    gems_obtained = 20 - (index - 1) * 2  # Rewards for promotion (adjust as needed)
                else:
                    advancement = "Retained"
                    gems_obtained = 10 if ul.xp_global > 0 else 0  # Retained users get a base reward
            else:
                # Normal league logic
                if total_users <= 3:
                    if ul.xp_global == 0:
                        advancement = "Demoted"
                        gems_obtained = 0
                    else:
                        advancement = "Retained"
                        gems_obtained = 10
                else:
                    if index <= promotion_threshold:
                        gems_obtained = 20 - (index - 1) * 2  # Reward for promotion
                        advancement = "Promoted"
                    elif index <= demotion_threshold:
                        gems_obtained = 10  # Retained users get a base reward
                        advancement = "Retained"
                    else:
                        gems_obtained = 0  # Demoted users receive no gems
                        advancement = "Demoted"

            # Prefix for S3 bucket URL
            s3_bucket_url = "https://video-play-api-bucket.s3.amazonaws.com/"

            # User data for each ranking
            rankings_data.append({
                "user_id": ul.user.id,
                "username": ul.user.username,
                "profile_picture": f"{s3_bucket_url}{ul.user.profile_picture}" if ul.user.profile_picture else None,
                "xp": ul.xp_global,
                "streaks": ul.user.streak,  # Assuming `streak` is a field on the user model
                "gems_obtained": gems_obtained,
                "rank": index,
                "advancement": advancement
            })

        # Find the current user's rank
        user_rank = next((index for index, r in enumerate(rankings_data, start=1) if r["user_id"] == user.id), None)

        league_start = league_instance.league_start.isoformat(timespec='milliseconds') + 'Z'
        league_end = league_instance.league_end.isoformat(timespec='milliseconds') + 'Z'

        # Response data
        data = {
            "league_id": league_instance.id,
            "league_name": league_instance.league.name,
            "league_level": 11 - league_instance.league.order,
            "league_start": league_start,
            "league_end": league_end,
            "user_rank": user_rank,
            "rankings": rankings_data
        }

        return Response(data, status=status.HTTP_200_OK)


class CompanyActiveLeagueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        user = request.user

        # Get the user's active company league instance
        user_league = (
            UserLeague.objects
            .filter(user=user, league_instance__is_active=True, league_instance__company__isnull=False)
            .select_related('league_instance', 'user')
            .first()
        )

        if not user_league:
            return Response({"error": "No active company league found for the user"}, status=404)

        league_instance = user_league.league_instance

        # Retrieve all leagues approved for the company
        approved_leagues = (
            LeagueInstance.objects
            .filter(company=league_instance.company, is_active=True)
            .select_related('league')
            .order_by('league__order')
        )

        # Get the highest and lowest leagues for the company
        lowest_league_order = approved_leagues.first().league.order
        highest_league_order = approved_leagues.last().league.order
        print(lowest_league_order)
        print(highest_league_order)

        rankings = UserLeague.objects.filter(league_instance=league_instance).select_related('user').order_by(
            '-xp_company', '-user__streak', 'id')
        total_users = rankings.count()
        promotion_threshold = int(total_users * 0.30)
        demotion_threshold = int(total_users * 0.80)

        is_highest_league = league_instance.league.order == highest_league_order
        is_lowest_league = league_instance.league.order == lowest_league_order

        rankings_data = []
        for index, ul in enumerate(rankings, start=1):
            if is_highest_league and is_lowest_league:
                # When the highest and lowest leagues are the same, all users are retained 
                advancement = "Retained"
                gems_obtained = 10 if ul.xp_global > 0 else 0
            elif is_highest_league:
                # Highest league: users can only be retained or demoted
                if index <= demotion_threshold:
                    advancement = "Retained"
                    gems_obtained = 10
                else:
                    advancement = "Demoted"
                    gems_obtained = 0  # No gems for demoted users
            elif is_lowest_league:
                # Lowest league: users can be promoted based on ranking (top 30%)
                if index <= promotion_threshold:
                    advancement = "Promoted"
                    gems_obtained = 20 - (index - 1) * 2  # Rewards for promotion (adjust as needed)
                else:
                    advancement = "Retained"
                    gems_obtained = 10 if ul.xp_global > 0 else 0  # Retained users get a base reward
            else:
                # Normal league logic
                if total_users <= 3:
                    if ul.xp_global == 0:
                        advancement = "Demoted"
                        gems_obtained = 0
                    else:
                        advancement = "Retained"
                        gems_obtained = 10
                else:
                    if index <= promotion_threshold:
                        gems_obtained = 20 - (index - 1) * 2  # Reward for promotion
                        advancement = "Promoted"
                    elif index <= demotion_threshold:
                        gems_obtained = 10  # Retained users get a base reward
                        advancement = "Retained"
                    else:
                        gems_obtained = 0  # Demoted users receive no gems
                        advancement = "Demoted"

            # Prefix for S3 bucket URL
            s3_bucket_url = "https://video-play-api-bucket.s3.amazonaws.com/"

            # Add user data
            rankings_data.append({
                "user_id": ul.user.id,
                "username": ul.user.username,
                "profile_picture": f"{s3_bucket_url}{ul.user.profile_picture}" if ul.user.profile_picture else None,
                "xp": ul.xp_company,
                "streaks": ul.user.streak,  # Assuming `streak` is a field on the user model
                "gems_obtained": gems_obtained,
                "rank": index,
                "advancement": advancement
            })

        # Find the current user's rank
        user_rank = next((index for index, r in enumerate(rankings_data, start=1) if r["user_id"] == user.id), None)

        league_start = league_instance.league_start.isoformat(timespec='milliseconds') + 'Z'
        league_end = league_instance.league_end.isoformat(timespec='milliseconds') + 'Z'

        # Response data
        data = {
            "league_id": league_instance.id,
            "league_name": league_instance.league.name,
            "league_level": 11 - league_instance.league.order,  # Reverse order for league level
            "league_start": league_start,
            "league_end": league_end,
            "user_rank": user_rank,
            "rankings": rankings_data
        }

        return Response(data, status=status.HTTP_200_OK)


class CompanyPastDrawsAPIView(APIView):
    """
    API view to retrieve all previous company draws (is_active=False) and their winners.
    """

    def get(self, request):
        # Get all previous company draws (is_active=False)
        company_draws = Draw.objects.filter(draw_type='company', is_active=False)
        data = []

        for draw in company_draws:
            # Serialize each draw
            draw_data = DrawSerializer(draw).data

            # Get winners for this draw
            winners = DrawWinner.objects.filter(draw=draw)
            winners_data = DrawWinnerSerializer(winners, many=True).data

            # Include draw data and winners in the response
            data.append({
                'draw': draw_data,
                'winners': winners_data,
            })

        return Response(data, status=status.HTTP_200_OK)


class GlobalPastDrawsAPIView(APIView):
    """
    API view to retrieve all previous global draws (is_active=False) and their winners.
    """

    def get(self, request):
        # Get all previous global draws (is_active=False)
        global_draws = Draw.objects.filter(draw_type='global', is_active=False)
        data = []

        for draw in global_draws:
            # Serialize each draw
            draw_data = DrawSerializer(draw).data

            # Get winners for this draw
            winners = DrawWinner.objects.filter(draw=draw)
            winners_data = DrawWinnerSerializer(winners, many=True).data

            # Include draw data and winners in the response
            data.append({
                'draw': draw_data,
                'winners': winners_data,
            })

        return Response(data, status=status.HTTP_200_OK)


class ApprovedLeaguesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the user's company
        company = request.user.company

        # Check if user has a company
        if not company:
            return Response({
                "detail": "User does not belong to any company.",
                "approved_leagues": [],
                "global_leagues": []
            })

        # Retrieve approved leagues for the user's company
        approved_leagues = (
            LeagueInstance.objects
            .filter(company=company, is_active=True)
            .select_related('league')
            .values("league__name", "league__order")
            .order_by("league__order")  # Sort by league order
        )
        # Modify the field names to match global leagues
        approved_leagues_data = [
            {"name": league["league__name"], "order": league["league__order"]}
            for league in approved_leagues
        ]

        # Retrieve all global leagues ordered by 'order'
        global_leagues = (
            League.objects
            .all()
            .values("name", "order")
            .order_by("order")  # Sort by league order
        )
        global_leagues_data = list(global_leagues)

        # Reverse the order numbers for global leagues
        for index, league in enumerate(reversed(global_leagues_data), start=1):
            league['order'] = index

        # Return both approved and global leagues
        return Response({
            "company_leagues": approved_leagues_data,
            "global_leagues": global_leagues_data
        })


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"error": "No refresh token provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FollowToggleAPIView(APIView):
    def post(self, request, user_id):
        user_to_follow = get_object_or_404(CustomUser, id=user_id)

        # Prevent users from following themselves
        if user_to_follow == request.user:
            return Response({"message": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        follow_instance, created = UserFollowing.objects.get_or_create(
            follower=request.user, following=user_to_follow
        )

        if not created:
            follow_instance.delete()
            return Response({"message": "Unfollowed"}, status=status.HTTP_200_OK)

        # Send follow notification
        send_followclap_notification(user_to_follow, "New Follower", f"{request.user.username} started following you.")

        return Response({"message": "Followed"}, status=status.HTTP_201_CREATED)


class ClapToggleAPIView(APIView):
    def post(self, request, feed_id):
        # Fetch the feed instance
        feed = get_object_or_404(Feed, id=feed_id)
        feed_creator = feed.user
        current_user = request.user

        # Check if the current user is either following the feed creator or in the same company
        is_following = UserFollowing.objects.filter(follower=current_user, following=feed_creator).exists()

        is_in_same_company = (
                current_user.company is not None and
                current_user.company == feed_creator.company
        )

        if not (is_following or is_in_same_company):
            return Response(
                {"detail": "You can only clap if you are following the user or are a member of the same company."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Toggle clap
        clap_instance, created = Clap.objects.get_or_create(user=current_user, feed=feed)
        if not created:
            clap_instance.delete()
            return Response({"message": "Unclapped"}, status=status.HTTP_200_OK)

        # Send clap notification
        send_followclap_notification(feed_creator, "New Clap", f"{current_user.username} clapped your feed.")

        return Response({"message": "Clapped"}, status=status.HTTP_201_CREATED)


class FeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class FeedListView(APIView):
    pagination_class = FeedPagination

    def get(self, request):
        user = request.user
        # Get the list of users the current user is following
        following_users = user.following.values_list('following', flat=True)

        user_timezone = user.timezone
        local_today = now().astimezone(user_timezone)
        last_week = local_today - timedelta(days=7)

        feeds = Feed.objects.filter(user__in=following_users, created_at__gte=last_week)

        # Fetch all feeds from users the current user follows also top clapped
        top_clapped = self.request.query_params.get('top_clapped', '').lower() == 'true'
        if top_clapped:
            feeds = feeds.order_by('-claps_count')[:10]
        else:
            feeds = feeds.order_by('-created_at')

        # Calculate the number of feeds the user has clapped for today
        today = local_today.date()
        user_claps_today = Clap.objects.filter(user=user, feed__user__in=following_users,
                                               created_at__date=today).count()

        # Paginate the results
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(feeds, request)

        # Serialize the feeds with the request context for `has_clapped`
        serializer = FeedSerializer(result_page, many=True, context={'request': request})

        return paginator.get_paginated_response(
            {
                'feeds': serializer.data,
                'user_claps_today': user_claps_today
            }
        )


class CompanyFeedListView(APIView):
    pagination_class = FeedPagination

    def get(self, request):
        user = request.user
        # Check if the user belongs to a company
        user_company = user.company
        if not user_company:
            return Response({"detail": "User is not part of a company"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the list of users in the same company as the current user, excluding the current user
        company_users = user_company.members.exclude(id=request.user.id).values_list('id', flat=True)

        user_timezone = user.timezone
        local_today = now().astimezone(user_timezone)
        last_week = local_today - timedelta(days=7)

        # Fetch all feeds from users in the same company as the current user, excluding their own posts
        feeds = Feed.objects.filter(user__in=company_users, created_at__gte=last_week)

        # Fetch all feeds from users the current user follows also top clapped
        top_clapped = self.request.query_params.get('top_clapped', '').lower() == 'true'
        if top_clapped:
            feeds = feeds.order_by('-claps_count')[:10]
        else:
            feeds = feeds.order_by('-created_at')

        # Calculate the number of feeds the user has clapped for today
        today = local_today.date()
        user_claps_today = Clap.objects.filter(user=user, feed__user__in=company_users, created_at__date=today).count()

        # Paginate the results
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(feeds, request)

        # Serialize the feeds with the request context for `has_clapped`
        serializer = FeedSerializer(result_page, many=True, context={'request': request})

        return paginator.get_paginated_response(
            {
                'feeds': serializer.data,
                'user_claps_today': user_claps_today
            }
        )


# class UserFeedView(APIView):
#     permission_classes = [IsAuthenticated]
#     pagination_class = FeedPagination

#     def get(self, request):
#         user = request.user

#         user_timezone = user.timezone
#         local_today = now().astimezone(user_timezone)
#         last_week = local_today - timedelta(days=7)

#         # Fetch user's own feeds from the last 7 days
#         feeds = Feed.objects.filter(user=user, created_at__gte=last_week).order_by('-created_at')

#         # Paginate the results
#         paginator = self.pagination_class()
#         result_page = paginator.paginate_queryset(feeds, request)

#         # Serialize the feeds with the request context for `has_clapped`
#         serializer = FeedSerializer(result_page, many=True, context={'request': request})

#         return paginator.get_paginated_response(serializer.data)

class UserFeedView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = FeedPagination

    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        local_today = now().astimezone(user_timezone)
        start_of_week = local_today - timedelta(days=local_today.weekday())  # Start of the current week (Monday)
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        print('start_of_week', start_of_week)

        # Fetch user's feeds
        feeds = Feed.objects.filter(user=user).order_by('-created_at')

        # Paginate the results
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(feeds, request)

        # Serialize the feeds
        serializer = FeedSerializer(result_page, many=True, context={'request': request})

        # Calculate weekly totals
        celebrations_this_week = Clap.objects.filter(feed__user=user, created_at__gte=start_of_week).count()
        gems_earned_this_week = Gem.objects.filter(
            user=user,
            date__gte=start_of_week.date()
        ).aggregate(
            total_gems=Sum(F('copy_xp_gem') + F('copy_manual_gem'))
        )['total_gems'] or 0
        tickets_exchanged_this_week = Purchase.objects.filter(
            user=user,
            item_name__in=['ticket_global', 'ticket_company'],
            timestamp__gte=start_of_week
        ).aggregate(total_tickets=Sum('quantity'))['total_tickets'] or 0

        # Add weekly_totals to the response
        response = paginator.get_paginated_response(serializer.data)
        response.data['weekly_totals'] = {
            "celebrations_this_week": celebrations_this_week,
            "gems_earned_this_week": gems_earned_this_week,
            "tickets_exchanged_this_week": tickets_exchanged_this_week
        }
        return response


class UserGemStatusView(APIView):
    """
    This view returns the gem status for the authenticated user.

    The response includes:
    - total_gems: The total number of gems the user currently has.
    - xp_gems_earned_today: The number of XP gems the user has earned today.
    - manual_gems_earned_today: The number of manual gems the user has earned today.
    - remaining_gems_today: The number of remaining gems the user can earn today, with a maximum of 5 per day.
    - all_time_gems: The total number of gems the user has earned all-time.
    - gems_per_day: A list of gems earned per day within the specified date range.

    The user's local time is used to determine the dates for querying the gem records.
    Permission: User must be authenticated.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Retrieve the user's timezone and calculate the current local date for the user
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone)
        today = user_local_time.date()

        # Get start and end dates from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', today)

        if not start_date:
            return Response({"error": "Please provide a start date."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch today's gem record
        gem_record = Gem.objects.filter(user=user, date=today).first()

        # Total gems the user currently has
        total_gems = user.get_gem_count()

        # Gems the user has earned today
        xp_gems_earned_today = gem_record.xp_gem if gem_record else 0
        manual_gems_earned_today = gem_record.manual_gem if gem_record else 0

        # Remaining gems the user can earn today
        remaining_gems_today = max(0, 5 - xp_gems_earned_today)

        # Fetch all-time gems
        all_time_gems = Gem.objects.filter(user=user).aggregate(total_gems=Sum('copy_xp_gem') + Sum('copy_manual_gem'))[
                            'total_gems'] or 0

        # Query gem records in the user's local date range, using the copy fields for historical data
        gem_records = Gem.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).annotate(
            xp_gems=F('copy_xp_gem'),
            manual_gems=F('copy_manual_gem')
        ).values('date', 'xp_gems', 'manual_gems').order_by('date')

        # Prepare gem data for each day
        gems_per_day = [
            {
                'date': record['date'],
                'xp_gems': record['xp_gems'],
                'manual_gems': record['manual_gems']
            }
            for record in gem_records
        ]

        # Include the present day's record if it doesn't exist
        if not any(record['date'] == today for record in gems_per_day):
            gems_per_day.append({
                'date': today,
                'xp_gems': xp_gems_earned_today,
                'manual_gems': manual_gems_earned_today
            })
        else:
            for record in gems_per_day:
                if record['date'] == today:
                    record['xp_gems'] = xp_gems_earned_today
                    record['manual_gems'] = manual_gems_earned_today

        return Response({
            "total_gems": total_gems,
            "xp_gems_earned_today": xp_gems_earned_today,
            "manual_gems_earned_today": manual_gems_earned_today,
            "remaining_gems_today": remaining_gems_today,
            "all_time_gems": all_time_gems,
            "gems_per_day": gems_per_day,
        }, status=status.HTTP_200_OK)


class GlobalLeagueStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get the last global league instance for the user, sorted by league_end date
        global_leagues = UserLeague.objects.filter(
            user=user, league_instance__company__isnull=True
        ).select_related('league_instance').order_by('-league_instance__league_end')
        print(global_leagues)

        if global_leagues.count() < 2:
            return Response({"error": "No previous global league found for the user"}, status=404)

        global_league = global_leagues[1]  # Get the second-to-last league instance

        data = self.get_league_status(global_league, user)
        return Response(data, status=status.HTTP_200_OK)

    def get_league_status(self, league, user):
        league_instance = league.league_instance
        rankings = UserLeague.objects.filter(league_instance=league_instance).select_related('user').order_by(
            '-xp_global', 'id')

        total_users = rankings.count()
        promotion_threshold = int(total_users * 0.30)
        demotion_threshold = int(total_users * 0.80)

        is_highest_league = league_instance.league.order == 10
        is_lowest_league = league_instance.league.order == 1

        for index, ul in enumerate(rankings, start=1):
            if ul.user == user:
                # Highest league logic
                if is_highest_league:
                    # Highest league: users can only be retained or demoted
                    if index <= demotion_threshold:
                        status = "Retained"
                    else:
                        status = "Demoted"
                elif is_lowest_league:
                    if index <= promotion_threshold:
                        status = "Promoted"
                    else:
                        status = "Retained"
                else:
                    if index <= promotion_threshold:
                        status = "Promoted"
                    elif index <= demotion_threshold:
                        status = "Retained"
                    else:
                        status = "Demoted"

                return {
                    "league_id": league_instance.id,
                    "league_name": league_instance.league.name,
                    "league_level": 11 - league_instance.league.order,
                    "league_end": league_instance.league_end.isoformat(timespec='milliseconds') + 'Z',
                    "status": status,
                    "rank": index
                }
        return {"error": "User not found in the league"}


class CompanyLeagueStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get the last global league instance for the user, sorted by league_end date
        company_leagues = UserLeague.objects.filter(
            user=user, league_instance__company__isnull=False
        ).select_related('league_instance').order_by('-league_instance__league_end')

        if company_leagues.count() < 2:
            return Response({"error": "No previous company league found for the user"}, status=404)

        company_league = company_leagues[1]  # Get the second-to-last league instance

        data = self.get_league_status(company_league, user)
        return Response(data, status=status.HTTP_200_OK)

    def get_league_status(self, league, user):

        league_instance = league.league_instance
        rankings = UserLeague.objects.filter(league_instance=league_instance).select_related('user').order_by(
            '-xp_company', 'id')

        total_users = rankings.count()
        promotion_threshold = int(total_users * 0.30)
        demotion_threshold = int(total_users * 0.80)

        # Get the highest and lowest league orders for the company
        approved_leagues = LeagueInstance.objects.filter(company=league_instance.company, is_active=True)
        lowest_league_order = approved_leagues.first().league.order
        highest_league_order = approved_leagues.last().league.order

        is_highest_league = league_instance.league.order == highest_league_order
        is_lowest_league = league_instance.league.order == lowest_league_order

        for index, ul in enumerate(rankings, start=1):
            if ul.user == user:
                # Highest league logic
                if is_highest_league:
                    # Highest league: users can only be retained or demoted
                    if index <= demotion_threshold:
                        status = "Retained"
                    else:
                        status = "Demoted"
                elif is_lowest_league:
                    if index <= promotion_threshold:
                        status = "Promoted"
                    else:
                        status = "Retained"
                else:
                    if index <= promotion_threshold:
                        status = "Promoted"
                    elif index <= demotion_threshold:
                        status = "Retained"
                    else:
                        status = "Demoted"

                return {
                    "league_id": league_instance.id,
                    "league_name": league_instance.league.name,
                    "league_level": 11 - league_instance.league.order,
                    "league_end": league_instance.league_end.isoformat(timespec='milliseconds') + 'Z',
                    "status": status,
                    "rank": index
                }
        return {"error": "User not found in the league"}


class CompanyDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interval: Literal["this_week", "this_month", "last_week"] = self.request.query_params.get(
            'interval') or "this_month"
        # Get the company associated with the logged-in user
        try:
            company = request.user.owned_company.first()
            if not company:
                return Response({"error": "No company found for this user"}, status=404)
        except Company.DoesNotExist:
            return Response({"error": "Company not found"}, status=404)

        # Get current date and 30 days ago date
        # get last date of this month
        (first_date, last_date) = get_last_day_and_first_day_of_this_month()

        # Get all unique employees (members) of the company
        company_members = Membership.objects.filter(company=company)
        total_employees = company_members.values('user').distinct().count()

        # Calculate global average XP for comparison
        global_avg_xp = Xp.objects.filter(
            date__range=[first_date, last_date]
        ).aggregate(
            global_avg=Avg('totalXpToday')
        )['global_avg'] or 0

        # Calculate company XP stats for last 30 days
        company_xp = Xp.objects.filter(
            user__membership__company=company,
            date__range=[first_date, last_date]
        ).aggregate(
            total_xp=Sum('totalXpToday'),
            avg_xp_per_user=Avg('totalXpToday')
        )
        # Get daily steps and XP for last 30 days
        # TODO: Compare if those to methods are equivalent by using the sames tests data
        daily_stats = get_daily_steps_and_xp(company, interval)
        # daily_stats = (
        #     DailySteps.objects.filter(
        #         user__membership__company=company,
        #         date__gte=thirty_days_ago
        #     ).values('date')
        #     .annotate(
        #         total_steps=Sum('step_count'),
        #         total_xp=Sum('user__xp_records__totalXpToday')
        #     ).order_by('date')
        # )
        # Get recent feed items (high performers and milestones)
        # TODO: probably add websocket consumer version of this
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        recent_feeds = Feed.objects.select_related("user").filter(
            user__membership__company=company,
            feed_type__in=['Milestone', 'Promotion'],
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')[:10]

        response_data = {
            'company_stats': {
                'total_employees': total_employees,
                # TODO(1): maybe use a different endpoint so that we can filter it by date
                'avg_xp_per_user': company_xp['avg_xp_per_user'] or 0,
                'global_avg_xp': global_avg_xp,
            },
            # TODO: same as TODO(1)
            'daily_stats': list(daily_stats),
            'recent_activities': [
                {
                    'user': EmployeeSerializer(feed.user).data,
                    'type': feed.feed_type,
                    'content': feed.content,
                    'timestamp': feed.created_at,
                } for feed in recent_feeds
            ]
        }

        return Response(response_data, status=status.HTTP_200_OK)


class NotificationPagination(PageNumberPagination):
    page_size = 20  # Number of notifications per page
    page_size_query_param = 'page_size'  # Allows the client to define the page size
    max_page_size = 100  # Maximum number of items per page


class NotificationsView(APIView):
    pagination_class = NotificationPagination  # Assign the pagination class here

    def get(self, request):
        # Get the current user
        user = request.user

        # Fetch notifications for the user, ordered by created_at (most recent first)
        notifications = Notif.objects.filter(user=user).order_by('-created_at')

        # Paginate the results
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(notifications, request)

        # Serialize the paginated results using NotifSerializer
        serializer = NotifSerializer(result_page, many=True, context={'request': request})

        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)


class EmployeeByCompanyModelDetailsView(RetrieveAPIView, DestroyAPIView):
    permission_classes = [IsCompanyOwner]
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CustomUser.objects.filter(company_id=company_id).select_related("company")

    def handle_exception(self, exc):
        if isinstance(exc, (ValueError, KeyError)):
            # Log the error
            logger.error(f"Exception occurred: {exc}")
            # Return a 500 Internal Server Error response
            return Response({"error": "An internal server error occurred."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return super().handle_exception(exc)


class EmployeeListView(ListAPIView):
    # TODO: add company owner pk based matching permission
    permission_classes = [IsAdminUser]
    serializer_class = EmployeeSerializer
    filter_backends = [rest_framework.DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = EmployeeFilterSet
    search_fields = ['first_name', 'last_name', 'email', 'username', ]
    ordering_fields = ['id', 'username', 'email', 'company__name', "date_joined"]

    def get_queryset(self):
        # company_id = self.kwargs['company_id']
        # current_user = self.request.user
        # # admin users can have access to all employees
        # queryset = CustomUser.objects.order_by('id')
        # # Company owner can only access data of his employees
        # if current_user.owned_company.filter(id=company_id).exists():
        #     queryset.filter(company_id=company_id, membership__role="employee")
        # if not the user is considered admin. The permission class allready einsure that other users do not have access to this
        queryset = CustomUser.objects.all().order_by("id").select_related("company")
        return queryset


class EmployeeByCompanyModelView(ListAPIView):
    permission_classes = [IsAdminUser | IsCompanyOwner]
    serializer_class = EmployeeSerializer
    filter_backends = [rest_framework.DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = EmployeeFilterSet
    search_fields = ['first_name', 'last_name', 'email', 'username', ]
    ordering_fields = ['id', 'username', 'email', 'company__name', "date_joined"]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CustomUser.objects.filter(company_id=company_id).order_by('id').select_related("company")

    def handle_exception(self, exc):
        if isinstance(exc, (ValueError, KeyError)):
            # Log the error
            logger.error(f"Exception occurred: {exc}")
            # Return a 500 Internal Server Error response
            return Response({"error": "An internal server error occurred."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return super().handle_exception(exc)


class EmployeeAdminModelView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer
    # TODO: filtering
    filterset_class = EmployeeFilterSet

    def get_queryset(self):
        # should be by employee too
        return CustomUser.objects.filter(membership__role="employee")


# endpoints for in house dashboard
# Global statistics for the in house dashboard
class GlobalStats(APIView):
    # TODO: refine permissions
    permission_classes = [IsAuthenticated]

    def get(self, request):
        all_users = CustomUser.objects.all()
        total_users = all_users.count()
        all_user_that_installed_app = all_users.exclude(last_login__isnull=True)
        percentage_of_install = all_user_that_installed_app.count() * 100 / total_users
        total_companies = Company.objects.count()

        data = {
            "total_users": total_users,
            "percentage_of_install": percentage_of_install,
            "total_companies": total_companies,
        }
        return Response(data=data)


# Xp graphs for 30 days
class GlobalXpGraph(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interval: Literal["this_week", "this_month", "last_week"] = self.request.query_params.get(
            'interval') or "this_month"
        xps_stats = get_global_xp_for_stats(interval)
        return Response(data=xps_stats)


class XpStatsByUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        interval: Literal["this_week", "this_month", "last_week"] = self.request.query_params.get(
            'interval') or "this_month"
        xps_stats = get_global_xp_for_stats_by_user(user_id, interval)
        return Response(data=xps_stats)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Token refresh view for custom token.
    """
    def post(self, request, *args, **kwargs):
        try:
            refresh = RefreshToken(request.data["refresh"])
            user_id = refresh["user_id"]

            # Check if user still exists
            if not CustomUser.objects.filter(id=user_id).exists():
                return Response({"detail": "Invalid token."}, status=401)
            
            # If user exists or refresh valid, continue to refresh the token       
            response = super().post(request, *args, **kwargs)
            
            # Blacklist the old refresh token
            refresh.blacklist()

            return response

        except TokenError as e:
            raise InvalidToken(e.args[0])


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain pair view./ Login view
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        email = request.data['username']

        # Attempt to get the user from the request
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise NotFound(detail="User not found.")

        # Retrieve the new refresh token issued in this request
        new_refresh_token = response.data['refresh']

        # Blacklist all previous refresh tokens for the user
        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        for token in outstanding_tokens:
            if str(token.token) != new_refresh_token:  # Exclude the newly issued token
                try:
                    BlacklistedToken.objects.create(token=token)
                except:
                    continue


        # Send email notification
        send_login_successful_email_task.delay_on_commit(user.id, email)

        return response


class CompanyEmployeeInvitationsListView(ListAPIView):
    serializer_class = InvitationAsEmployeeSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = InvitationFilterSet
    filter_backends = [SearchFilter, rest_framework.DjangoFilterBackend, OrderingFilter]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ['id', 'first_name', 'email', 'last_name', 'status', 'date_sent']

    def get_queryset(self):
        company_id = self.kwargs["pk"]
        return Invitation.objects.order_by("id").select_related("company", "invited_user", "invited_by").filter(company_id=company_id)

# TODO: move to filter module
class DrawFilter(filters.FilterSet):
    draw_date_after = filters.DateTimeFilter(field_name='draw_date', lookup_expr='gte')
    draw_date_before = filters.DateTimeFilter(field_name='draw_date', lookup_expr='lte')
    
    class Meta:
        model = Draw
        fields = ['draw_type', 'company', 'is_active']

class ManualDrawViewSet(viewsets.ModelViewSet):
    queryset = Draw.objects.all().select_related('company')
    serializer_class = ManualDrawCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = DrawFilter
    search_fields = ['draw_name']
    ordering_fields = ['draw_date', 'created_at']

class PrizeFilter(filters.FilterSet):
    value_min = filters.NumberFilter(field_name='value', lookup_expr='gte')
    value_max = filters.NumberFilter(field_name='value', lookup_expr='lte')
    
    class Meta:
        model = Prize
        fields = ['draw', 'quantity', 'value_min', 'value_max']

class ManualPrizeViewSet(viewsets.ModelViewSet):
    queryset = Prize.objects.all().select_related('draw')
    serializer_class = ManualPrizeCreateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = PrizeFilter
    search_fields = ['name', 'description']
    ordering_fields = ['value', 'quantity', 'created_at']
