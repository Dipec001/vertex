from django.urls import path
from . import views

urlpatterns = [
    path('validate-email-password/', views.ValidateEmailPasswordView.as_view(), name='validate_email_password'),
    path('validate-company-association/', views.ValidateCompanyAssociationView.as_view(), name='validate_company_association'),
    path('create-user/', views.NormalUserSignupView.as_view(), name='create_user'),
    path('signup-company-owner/', views.CompanyOwnerSignupView.as_view(), name='signup_company_owner'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('companies/<int:company_id>/invitations/', views.SendInvitationView.as_view(), name='send_invitation'),
    path('google-signin/', views.GoogleSignInView.as_view(), name='google_sign_in'),
    path('apple-signin/', views.AppleSignInView.as_view(), name='apple_sign_in'),
    path('facebook-signin/', views.FacebookSignInView.as_view(), name='facebook_sign_in'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('transfer-company/', views.TransferOwnershipView.as_view(), name='transfer_company_ownership'),
    path('daily-steps/', views.DailyStepsView.as_view(), name='daily-steps'),
    path('workout/', views.WorkoutActivityView.as_view(), name='workout'),
    path('xp/', views.XpRecordsView.as_view(), name='xp-records'),
    path('streak/', views.StreakRecordsView.as_view(), name='streak-records'),
    path('convert-xp/', views.ConvertXPView.as_view(), name='convert-xp'),
    path('purchase-history/', views.PurchaseHistoryView.as_view(), name='purchase-history'),
]