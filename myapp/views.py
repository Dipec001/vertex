from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CompanyOwnerSignupSerializer, NormalUserSignupSerializer, InvitationSerializer, UserProfileSerializer, UpdateProfileSerializer
from .models import CustomUser, Invitation, Company, Membership
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings
from .google_validate import validate_google_token
from .apple_validate import validate_apple_token
from .facebook_validate import validate_facebook_token
import requests
from allauth.socialaccount.models import SocialAccount
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

# class NormalUserSignupView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = NormalUserSignupSerializer(data=request.data)
        
#         # Check if data is valid
#         if serializer.is_valid():

#             # Associate user with company based on invitation
#             company_email_or_code = request.data.get('company_email_or_code')
#             if not company_email_or_code:
#                 return Response({"error": "Company email or invite code is required."}, status=status.HTTP_400_BAD_REQUEST)
#             try:
#                 if '@' in company_email_or_code:
#                     invitation = Invitation.objects.get(email=company_email_or_code, status='pending')
#                 else:
#                     invitation = Invitation.objects.get(invite_code=company_email_or_code, status='pending')
#             except Invitation.DoesNotExist:
#                 return Response({"error": "Invalid company email or invite code"}, status=status.HTTP_400_BAD_REQUEST)

#             # Update invitation status and associate the user with the company
#             invitation.status = 'accepted'
#             invitation.save()
#             company = invitation.company
#             user = serializer.save()

#             # Check if the user is already a member of the company
#             if company.members.filter(id=user.id).exists():
#                 return Response({"error": "User is already a member of this company."}, status=status.HTTP_400_BAD_REQUEST)
            
#             company.members.add(user)

#             return Response({"success": "User created successfully"}, status=status.HTTP_201_CREATED)
        
#         # Return validation errors
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

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

        # Get Google's unique user ID (sub)
        google_uid = decoded_token.get('sub')
        if not google_uid:
            return Response({'error': 'Invalid token format'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the user's email
        email = decoded_token.get('email')
        if not email:
            return Response({'error': 'User does not have an email address'}, status=status.HTTP_400_BAD_REQUEST)
        
        picture = decoded_token.get('picture', '')


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
                "picture": picture
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
            if email is None:
                return Response({'error': 'Email is required on first sign-in'}, status=status.HTTP_400_BAD_REQUEST)
        
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
                "login_type": "apple"
            }, status=status.HTTP_200_OK)

        

class FacebookSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.data.get('access_token')

        if not access_token:
            return Response({"error": "Access token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = validate_facebook_token(access_token)

            # Retrieve user information from Facebook
            user_info_url = f"https://graph.facebook.com/v10.0/{user_id}?fields=id,name,email&access_token={access_token}"
            user_info_response = requests.get(user_info_url)
            user_info = user_info_response.json()

            # Extract user details
            email = user_info.get('email')
            name = user_info.get('name')
            user = CustomUser.objects.filter(email=email).first()

            if user:
                # User exists, return access and refresh tokens
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "is_new_user": False,
                    "message": "User logged in successfully."
                }, status=status.HTTP_200_OK)

            return Response({
                "is_new_user": True,
                "message": "User validated successfully.",
                "email": email,
                "name": name
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class FacebookSignInView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         facebook_token = request.data.get('access_token')

#         if not facebook_token:
#             return Response({'error': 'Facebook access token is required'}, status=status.HTTP_400_BAD_REQUEST)

#         # Verify Facebook token and get user info
#         user_info_url = f'https://graph.facebook.com/me?access_token={facebook_token}&fields=id,name,email'
#         response = requests.get(user_info_url)

#         if response.status_code != 200:
#             return Response({'error': 'Invalid Facebook token or request failed'}, status=status.HTTP_400_BAD_REQUEST)

#         user_info = response.json()
#         facebook_uid = user_info.get('id')
#         email = user_info.get('email')

#         if not facebook_uid:
#             return Response({'error': 'Failed to retrieve user information from Facebook'}, status=status.HTTP_400_BAD_REQUEST)

#         # Check if a social account or user already exists
#         try:
#             social_account = SocialAccount.objects.get(uid=facebook_uid, provider='facebook')
#             user = social_account.user

#             # User exists, return access and refresh tokens
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 "access_token": str(refresh.access_token),
#                 "refresh_token": str(refresh),
#                 "is_new_user": False,
#                 "message": "User logged in successfully."
#             }, status=status.HTTP_200_OK)

#         except SocialAccount.DoesNotExist:
#             # If user doesn't exist, handle accordingly
#             existing_user = CustomUser.objects.filter(email=email).first()
#             if existing_user:
#                 return Response({
#                     'error': 'User with this email already exists',
#                     'suggestion': 'Please log in with this email or use a different method to sign up.',
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Create new user and social account
#             new_user = CustomUser.objects.create(email=email, username=user_info.get('name'))
#             SocialAccount.objects.create(user=new_user, uid=facebook_uid, provider='facebook')

#             # Return access and refresh tokens for new user
#             refresh = RefreshToken.for_user(new_user)
#             return Response({
#                 "access_token": str(refresh.access_token),
#                 "refresh_token": str(refresh),
#                 "is_new_user": True,
#                 "message": "User signed up and logged in successfully."
#             }, status=status.HTTP_200_OK)


class SocialUserSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        invitation_id = request.data.get('invitation_id')
        login_type = request.data.get('login_type')
        uid = request.data.get('uid', '')
        username = request.data.get('uid')

        if not email or not invitation_id:
            return Response({"error": "email and invitation ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the invitation to associate the user with the company
        try:
            invitation = Invitation.objects.get(id=invitation_id, status='pending')
        except Invitation.DoesNotExist:
            return Response({"error": "Invalid invitation."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email is already taken
        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the user
        user = CustomUser.objects.create_user(
            email=invitation.email,
            username=email.split("@")[0],
            password=None  # No password needed since they're signing in with Google
        )

        # Update the invitation status
        invitation.status = 'accepted'
        invitation.save()

        # Return success
        return Response({"success": "User created successfully"}, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"success": "Profile updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

