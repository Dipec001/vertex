from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (CompanyOwnerSignupSerializer, NormalUserSignupSerializer, 
                          InvitationSerializer, UserProfileSerializer, UpdateProfileSerializer, 
                          DailyStepsSerializer, WorkoutActivitySerializer,PurchaseSerializer, 
                          DrawWinnerSerializer, DrawEntrySerializer, DrawSerializer)
from .models import (CustomUser, Invitation, Company, Membership, DailySteps, Xp, WorkoutActivity,
                     Streak, Purchase, DrawWinner, DrawEntry,Draw, UserLeague, LeagueInstance)
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import render
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
from django.db.models import Sum
from .timezone_converter import convert_from_utc, convert_to_utc
from datetime import datetime
from rest_framework.exceptions import PermissionDenied
from zoneinfo import ZoneInfo
from django.utils.dateparse import parse_date
import pytz

# Create your views here.

class ValidateEmailPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        # Ensure email and password are provided
        if not email or not password or not confirm_password:
            return Response({"error": "Email, password, and confirm password are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if passwords match
        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email is already registered
        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # If everything is valid, return success
        return Response({
            "success": "Email and password are valid.",
            "login_type" : "Email and password"
            }, status=status.HTTP_200_OK)


class ValidateCompanyAssociationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        company_email_or_code = request.data.get('company_email_or_code')
        print(company_email_or_code)

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
            return Response({"error": "You do not have permission to send invitations."}, status=status.HTTP_403_FORBIDDEN)
        
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
            return Response({"error": "You do not have permission to view these invitations."}, status=status.HTTP_403_FORBIDDEN)

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
        email = decoded_token.get('email') # ONly returned on first login
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
            return Response({'error': 'Failed to retrieve user information from Facebook'}, status=status.HTTP_400_BAD_REQUEST)

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
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            profile_picture = request.FILES.get('profile_picture')
            if profile_picture:
                image_url = save_image_to_s3(profile_picture, 'profile_pictures')
                if image_url:
                    serializer.save(profile_picture=image_url)  # Save the URL instead
                else:
                    return Response({"error": "Failed to upload image to S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                serializer.save()  # Save without updating the profile picture

            return Response({"success": "Profile updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user

        # Prevent company owners from deleting their account without transferring ownership
        if user.is_company_owner:  # Check if the user owns a company
            return Response({"error": "You cannot delete your account while owning a company. Please transfer ownership first."}, status=status.HTTP_400_BAD_REQUEST)
        
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
        end_date = request.query_params.get('end_date', timezone.now().date())

        # Get the user's timezone from their profile (ZoneInfo object)
        user_timezone = ZoneInfo(request.user.timezone.key)

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

        # Prepare the data to include both steps and XP for each day in the user's timezone
        steps_data = []
        for step in steps_in_range:
            # Convert `timestamp` to the user's timezone, then use the date part
            date_in_user_timezone = step['timestamp'].astimezone(user_timezone).date()
            steps_data.append({
                'date': date_in_user_timezone,
                'total_steps': step['total_steps'],
                'total_xp': step['total_xp']
            })

        # Query total steps for the user across all time
        total_steps_count = DailySteps.objects.filter(user=request.user).aggregate(total_steps=Sum('step_count'))['total_steps'] or 0

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
            date = daily_steps.timestamp.date()
            user_xp = Xp.objects.filter(user=request.user, timeStamp__date=date).first()
            
            # Prepare the response, handle the case where no XP record exists yet
            xp_data = {
                'totalXpToday': user_xp.totalXpToday if user_xp else 0,
                'totalXpAllTime': user_xp.totalXpAllTime if user_xp else 0,
            }

            return Response({
                'data': serializer.data,  # Serialized daily steps data
                'xp': xp_data  # XP data for the current day
            }, status=status.HTTP_201_CREATED)

        # If the serializer is not valid, return the validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkoutActivityView(APIView):

    def get(self, request):
        user = request.user
        activities = WorkoutActivity.objects.filter(user=user)
        serializer = WorkoutActivitySerializer(activities, many=True)

        # Convert timestamps back to the user's timezone
        user_timezone_str = str(user.timezone)  # Get user's timezone as a string

        # Convert timestamps back to the user's timezone
        for activity in serializer.data:
            # Convert the string back to a datetime object
            activity['start_datetime'] = datetime.fromisoformat(activity['start_datetime'])
            activity['end_datetime'] = datetime.fromisoformat(activity['end_datetime'])

            # Now convert from UTC to user's timezone
            activity['start_datetime'] = convert_from_utc(user_timezone_str, activity['start_datetime'])
            activity['end_datetime'] = convert_from_utc(user_timezone_str, activity['end_datetime'])

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):

        # Convert user timezone to string if necessary
        user_timezone_str = str(request.user.timezone)

        # Extract and convert datetimes
        starttime_str = request.data['start_datetime']
        endtime_str = request.data['end_datetime']
        
        # Use fromisoformat to handle ISO datetime strings
        start_naive_datetime = datetime.fromisoformat(starttime_str)
        end_naive_datetime = datetime.fromisoformat(endtime_str)
        
        # Convert to UTC
        start_datetime = convert_to_utc(user_timezone_str, start_naive_datetime)
        end_datetime = convert_to_utc(user_timezone_str, end_naive_datetime)

        # Create a mutable copy of request.data and update the datetime fields
        updated_data = request.data.copy()
        updated_data['start_datetime'] = start_datetime.isoformat()  # Ensure it's in ISO format
        updated_data['end_datetime'] = end_datetime.isoformat()      # Ensure it's in ISO format

        # Pass the updated data to the serializer
        serializer = WorkoutActivitySerializer(data=updated_data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

class StreakRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())

        if not start_date:
            return Response({"error": "Please provide a start date."}, status=400)

        # Query streak records in the date range for the user
        streak_in_range = Streak.objects.filter(
            user=user,
            timeStamp__date__range=[start_date, end_date]
        ).values('timeStamp__date').annotate(current_streak=Sum('currentStreak')).order_by('timeStamp__date')

        # Prepare the data
        streak_data = [{'date': streak['timeStamp__date'], 'current_streak': streak['current_streak']} for streak in streak_in_range]

        current_date = timezone.now().date()
        previous_date = current_date - timezone.timedelta(days=1)

        # Retrieve yesterday's streak record
        previous_streak_record = Streak.objects.filter(user=user, timeStamp__date=previous_date).first()

        if previous_streak_record:
            current_streak = previous_streak_record.currentStreak
        else:
            current_streak = 0  # If no streak from yesterday, the streak resets to 0

        return Response({
            'streak_per_day': streak_data,
            'overall_current_streak': current_streak
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

        # Get user's timezone from the model
        user_timezone = request.user.timezone  # Assuming timezone is stored in user model

        # Make the start and end dates timezone-aware using user's timezone
        local_tz = pytz.timezone(user_timezone.key)
        start_date_local = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), local_tz)
        end_date_local = timezone.make_aware(datetime.combine(end_date, datetime.max.time()), local_tz)

        # Convert to UTC for querying the database
        start_date_utc = start_date_local.astimezone(pytz.UTC)
        end_date_utc = end_date_local.astimezone(pytz.UTC)

        # Query XP records in the UTC-adjusted date range for the user
        xp_in_range = Xp.objects.filter(
            user=request.user,
            timeStamp__range=[start_date_utc, end_date_utc]
        ).values('timeStamp__date').annotate(total_xp=Sum('totalXpToday')).order_by('timeStamp__date')

        xp_data = []

        # Loop over each day and fetch movement and mindfulness XP for that day
        for xp in xp_in_range:
            current_date = xp['timeStamp__date']

            # Fetch movement and mindfulness XP for the current date
            movement_xp = WorkoutActivity.objects.filter(
                user=request.user,
                start_datetime__date=current_date,  # Filter based on start_datetime date,
                activity_type="movement"
            ).aggregate(movement_xp=Sum('xp'))['movement_xp'] or 0

            mindfulness_xp = WorkoutActivity.objects.filter(
                user=request.user,
                start_datetime__date=current_date,  # Filter based on start_datetime date,
                activity_type="mindfulness"
            ).aggregate(mindfulness_xp=Sum('xp'))['mindfulness_xp'] or 0

            # Append data for the current date
            xp_data.append({
                'date': current_date,
                'total_xp': xp['total_xp'],
                'movement_xp': movement_xp,
                'mindfulness_xp': mindfulness_xp
            })

        # Fetch the actual total XP gained (across all time)
        total_xp_gained = Xp.objects.filter(user=request.user).aggregate(total_xp=Sum('totalXpToday'))['total_xp'] or 0

        # Return response with the breakdown per day, total XP gained, and remaining XP gained
        return Response({
            'xp_per_day': xp_data,
            'total_xp_gained': total_xp_gained,  # Sum of all XP across all time
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

        if item_type not in self.GEM_COSTS:
            return Response({"error": "Invalid item type"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the quantity is a positive integer
        if not isinstance(quantity, int) or quantity <= 0:
            return Response({"error": "Quantity must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)

        gem_cost_per_item = self.GEM_COSTS[item_type]
        total_gem_cost = gem_cost_per_item * quantity

        # Check if the user has enough available gems
        if user.gem < total_gem_cost:
            return Response({"error": f"Not enough gems to purchase. You need {total_gem_cost} gems for {quantity} {item_type}(s)."}, status=status.HTTP_400_BAD_REQUEST)

        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Deduct the total gem cost
            user.gem -= total_gem_cost
            user.gems_spent += total_gem_cost
            user.save(update_fields=['gem', 'gems_spent'])

            # Update the user's tickets or streak savers
            if item_type == 'streak_saver':
                user.streak_savers += quantity
            elif item_type == 'ticket_global':  # For tickets
                user.global_tickets += quantity

                global_draw = Draw.objects.filter(is_active=True, draw_type='global').first()
                if global_draw:
                    for _ in range(quantity):  # Add as many entries as tickets purchased
                        DrawEntry.objects.create(user=user, draw=global_draw)

            elif item_type == 'ticket_company':  # For company tickets
                user.company_tickets += quantity

            user.save(update_fields=['streak_savers', 'company_tickets','global_tickets'])

            # Record the purchase
            purchase_data = {
                'item_name': item_type,
                'gem_used': total_gem_cost,
                'quantity': quantity
            }
            purchase_serializer = PurchaseSerializer(data=purchase_data)

            if purchase_serializer.is_valid():
                purchase_serializer.save(user=user)  # Save the purchase with the user
            else:
                return Response(purchase_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"You have successfully converted {total_gem_cost} gems for {quantity} {item_type}(s).",
            "remaining_gem": user.gem
        }, status=status.HTTP_200_OK)


class PurchaseHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Fetch user's purchase history, excluding streak savers
        purchases = Purchase.objects.filter(user=user).exclude(item_name='streak_saver')
        
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
        serializer = DrawSerializer(draws, many=True, context={'request': request})
        return Response(serializer.data)


class GlobalDrawEditView(APIView):
    """
    View for editing global draws.
    Any user can view draw details, but only admin users can edit.
    """
    
    def get_object(self, pk):
        try:
            return Draw.objects.get(pk=pk, draw_type='global')  # Adjust based on your draw type logic
        except Draw.DoesNotExist:
            return None

    def get(self, request, pk):
        # Allow all users to view the draw details
        draw = self.get_object(pk)
        if draw is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DrawSerializer(draw, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        # Only allow admin users to edit the draw details
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        draw = self.get_object(pk)
        if draw is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DrawSerializer(draw, data=request.data, partial=True)  # Enable partial updates
        if serializer.is_valid():
            video = request.FILES.get('video')
            if video:
                image_url = save_image_to_s3(video, 'draw_videos')
                if image_url:
                    serializer.save(video=image_url)  # Save the URL instead
                else:
                    return Response({"error": "Failed to upload image to S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                serializer.save()  # Save without updating the profile picture

            return Response({"success": "Draw updated successfully"}, status=status.HTTP_200_OK)

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
                return Response({'detail':'No data passed'},status=status.HTTP_400_BAD_REQUEST)
            serializer = DrawSerializer(draw, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                # Use the custom update method here
                serializer.update(draw, serializer.validated_data)  
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Draw.DoesNotExist:
            raise PermissionDenied("You do not have permission to access or manage this draw.")


class EnterDrawView(APIView):
    """
    This view is used to enter a company draw
    """
    def post(self, request, pk):
        try:
            # Get the draw, ensure it's active and the user is a member of the company (if required)
            draw = Draw.objects.get(pk=pk, company__membership__user=self.request.user)

            # Check if the draw is active
            if not draw.is_active:
                return Response({'error': 'This draw is not active.'}, status=status.HTTP_400_BAD_REQUEST)

            # Get the ticket amount from the request, default to 1 if not provided
            ticket_amount = request.data.get('ticket_amount', 1)

            # Ensure the user has enough company tickets to enter the draw
            if request.user.company_tickets < ticket_amount:
                return Response({'error': 'You do not have enough company tickets to enter the draw.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create multiple entries for the user if ticket_amount > 1
            entries = [DrawEntry(user=request.user, draw=draw) for _ in range(ticket_amount)]
            DrawEntry.objects.bulk_create(entries)

            # Deduct the used tickets from the user's company tickets
            request.user.company_tickets -= ticket_amount
            request.user.save()

            return Response({'success': f'You have entered the draw with {ticket_amount} tickets. Your company ticket count has been reduced by {ticket_amount}.'}, status=status.HTTP_201_CREATED)

        except Draw.DoesNotExist:
            return Response({'error': 'You do not have permission to enter this draw or it does not exist.'}, status=status.HTTP_404_NOT_FOUND)


# class ExitDrawView(APIView):
#     """
#     This view is used to exit a company draw
#     """
#     def post(self, request, pk):
#         try:
#             # Get the draw, ensure it's active and the user is a member of the company (if required)
#             draw = Draw.objects.get(pk=pk, company__membership__user=self.request.user)

#             # Check if the draw is active
#             if not draw.is_active:
#                 return Response({'error': 'This draw is not active.'}, status=status.HTTP_400_BAD_REQUEST)

#             # Check if the user has any entries in the draw
#             entries = DrawEntry.objects.filter(draw=draw, user=request.user)
#             if not entries.exists():
#                 return Response({'error': 'You are not entered in this draw.'}, status=status.HTTP_400_BAD_REQUEST)

#             # Get the ticket amount from the request, default to remove all entries if not provided
#             ticket_amount = request.data.get('ticket_amount', None)

#             if ticket_amount is None:

#                 # Return the user's tickets based on the number of entries they had
#                 entry_count = entries.count()
#                 # Remove all entries for the user
#                 entries.delete()
#                 print("entry_count", entry_count)
#                 request.user.company_tickets += entry_count
#                 request.user.save()

#                 return Response({'success': f'You have completely left the draw. {entry_count} tickets have been returned to your account.'}, status=status.HTTP_200_OK)
#             else:
#                 # If ticket_amount is provided, delete up to that number of entries
#                 # Convert the queryset to a list and delete manually
#                 entries_to_delete = list(entries[:ticket_amount])
#                 entries_to_delete_count = len(entries_to_delete)

#                 # Delete each entry manually
#                 for entry in entries_to_delete:
#                     entry.delete()

#                 # Return tickets only for the entries that were deleted
#                 request.user.company_tickets += entries_to_delete_count
#                 request.user.save()

#                 return Response({'success': f'You have left {entries_to_delete_count} entries from the draw. {entries_to_delete_count} tickets have been returned to your account.'}, status=status.HTTP_200_OK)

#         except Draw.DoesNotExist:
#             return Response({'error': 'You do not have permission to leave this draw or it does not exist.'}, status=status.HTTP_404_NOT_FOUND)


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
            serializer = DrawSerializer(draws, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Membership.DoesNotExist:
            return Response({"error": "User does not belong to any company."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GlobalActiveLeagueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        user = request.user

        user_league = (
            UserLeague.objects
            .filter(user=user, league_instance__is_active=True, league_instance__league_end__gt=now, league_instance__company__isnull=True)
            .select_related('league_instance')
            .first()
        )

        if not user_league:
            return Response({"error": "No active global league found for the user"}, status=404)

        league_instance = user_league.league_instance
        rankings = UserLeague.objects.filter(league_instance=league_instance).order_by('-xp_global')

        data = {
            "league_name": league_instance.league.name,
            "league_start": league_instance.league_start,
            "league_end": league_instance.league_end,
            "user_rank": next(
                (index + 1 for index, ul in enumerate(rankings) if ul.user == user),
                None
            ),
            "rankings": [
                {
                    "username": ul.user.username,
                    "xp": ul.xp_global
                }
                for ul in rankings
            ]
        }

        return Response(data, status=status.HTTP_200_OK)


class CompanyActiveLeagueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        user = request.user

        user_league = (
            UserLeague.objects
            .filter(user=user, league_instance__is_active=True, league_instance__league_end__gt=now, league_instance__company__isnull=False)
            .select_related('league_instance')
            .first()
        )

        if not user_league:
            return Response({"error": "No active company league found for the user"}, status=404)

        league_instance = user_league.league_instance
        rankings = UserLeague.objects.filter(league_instance=league_instance).order_by('-xp_company')

        data = {
            "league_name": league_instance.league.name,
            "league_start": league_instance.league_start,
            "league_end": league_instance.league_end,
            "user_rank": next(
                (index + 1 for index, ul in enumerate(rankings) if ul.user == user),
                None
            ),
            "rankings": [
                {
                    "username": ul.user.username,
                    "xp": ul.xp_company
                }
                for ul in rankings
            ]
        }

        return Response(data, status=status.HTTP_200_OK)