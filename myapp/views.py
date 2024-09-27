from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CompanyOwnerSignupSerializer, NormalUserSignupSerializer, InvitationSerializer, UserProfileSerializer, UpdateProfileSerializer
from .models import CustomUser, Invitation, Company
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
        return Response({"success": "Email and password are valid."}, status=status.HTTP_200_OK)


class ValidateCompanyAssociationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        company_email_or_code = request.data.get('company_email_or_code')

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
        serializer = NormalUserSignupSerializer(data=request.data)
        
        # Check if data is valid
        if serializer.is_valid():

            # Associate user with company based on invitation
            company_email_or_code = request.data.get('company_email_or_code')
            if not company_email_or_code:
                return Response({"error": "Company email or invite code is required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                if '@' in company_email_or_code:
                    invitation = Invitation.objects.get(email=company_email_or_code, status='pending')
                else:
                    invitation = Invitation.objects.get(invite_code=company_email_or_code, status='pending')
            except Invitation.DoesNotExist:
                return Response({"error": "Invalid company email or invite code"}, status=status.HTTP_400_BAD_REQUEST)

            # Update invitation status and associate the user with the company
            invitation.status = 'accepted'
            invitation.save()
            company = invitation.company
            user = serializer.save()

            # Check if the user is already a member of the company
            if company.members.filter(id=user.id).exists():
                return Response({"error": "User is already a member of this company."}, status=status.HTTP_400_BAD_REQUEST)
            
            company.members.add(user)

            return Response({"success": "User created successfully"}, status=status.HTTP_201_CREATED)
        
        # Return validation errors
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
    
# class CustomLoginView(APIView):
#     def post(self, request):
#         email = request.data.get('email')
#         password = request.data.get('password')

#         # Authenticate user
#         user = authenticate(request, email=email, password=password)

#         if user is not None:
#             # Generate JWT tokens for the authenticated user
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 'access': str(refresh.access_token),
#                 'refresh': str(refresh),
#                 'email': user.email,
#                 'username': user.username,
#             }, status=status.HTTP_200_OK)
#         else:
#             return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


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
    "This endpoint is used to send an invitation by the company owner or HR"

    permission_classes = [IsAuthenticated]
    def post(self, request, company_id):
        company = Company.objects.get(id=company_id) # Fetch the company based on the ID
        serializer = InvitationSerializer(data=request.data, context={'request': request, 'company': company})

        if serializer.is_valid():
            serializer.save()
            return Response({"success": "Invitation sent successfully."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request, company_id):
        company = Company.objects.get(id=company_id)

        # Ensure the user is the company owner
        if company.owner != request.user:
            return Response({"error": "You do not have permission to view these invitations."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch all invitations for the company
        invitations = Invitation.objects.filter(company=company)
        serializer = InvitationSerializer(invitations, many=True, context={'request': request, 'company': company})

        return Response(serializer.data, status=status.HTTP_200_OK)


class GoogleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')

        if not id_token:
            return Response({"error": "ID token is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the Google ID token
        token_info = validate_google_token(id_token)
        print(token_info)

        if not token_info:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        # Extract user information from token_info
        email = token_info.get('email')
        name = token_info.get('name')
        picture = token_info.get('picture', '')
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

        # Return email for company association step
        return Response({
            "is_new_user": True,
            "message": "User validated successfully.",
            "email": email,
            "name": name,
            "picture": picture
        }, status=status.HTTP_200_OK)


class AppleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')

        if not id_token:
            return Response({"error": "ID token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_info = validate_apple_token(id_token)

            # Process token_info, e.g., extract email or user info
            email = token_info.get('email')
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
                "email": email
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

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


class SocialUserSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        invitation_id = request.data.get('invitation_id')

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

