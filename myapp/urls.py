from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'draws', views.ManualDrawViewSet, basename='manual-draw')
router.register(r'prizes', views.ManualPrizeViewSet, basename='manual-prize')
router.register(r'combined-draw-prizes', views.CombinedDrawPrizeViewSet, basename='combined-draw-prizes')

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('sentry-debug/', trigger_error),
    
    # WEBSOCKET TEST URLS
    path('test-league-rankings/', views.test_league_rankings, name='test-league-rankings'),
    path('test-streak/', views.test_streak_view, name='test_streak'),
    path('test-gem/', views.test_gem_view, name='test_gem'),
    path('test-feed/', views.test_feed_view, name='test_feed'),
    path('test-draw/', views.test_draw_view, name='test_draw'),
    path('test-noti/', views.test_noti_view, name='test_noti'),
    path('test-error/', views.test_error, name='test-error'),

    path('validate-email-password/', views.ValidateEmailPasswordView.as_view(), name='validate_email_password'),
    path('validate-company-association/', views.ValidateCompanyAssociationView.as_view(), name='validate_company_association'),
    path('verify-username/', views.VerifyUsernameView.as_view(), name='verify-username'),
    path('create-user/', views.NormalUserSignupView.as_view(), name='create_user'),
    path('signup-company-owner/', views.CompanyOwnerSignupView.as_view(), name='signup_company_owner'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('companies/<int:company_id>/invitations/', views.SendInvitationView.as_view(), name='send_invitation'),
    path('companies/<int:company_id>/bulk-invite/', views.SendInvitationViewInBulk.as_view(), name='send-bulk-invite'),
    path('google-signin/', views.GoogleSignInView.as_view(), name='google_sign_in'),
    path('apple-signin/', views.AppleSignInView.as_view(), name='apple_sign_in'),
    path('facebook-signin/', views.FacebookSignInView.as_view(), name='facebook_sign_in'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('transfer-company/', views.TransferOwnershipView.as_view(), name='transfer_company_ownership'),
    path('daily-steps/', views.DailyStepsView.as_view(), name='daily-steps'),
    path('workout/', views.WorkoutActivityView.as_view(), name='workout'),
    path('xp/', views.XpRecordsView.as_view(), name='xp-records'),
    path('streak/', views.StreakRecordsView.as_view(), name='streak-records'),
    path('convert-gem/', views.ConvertGemView.as_view(), name='convert-gem'),
    path('purchase-history/', views.PurchaseHistoryView.as_view(), name='purchase-history'),
    path('draws/global/<int:pk>/', views.GlobalDrawEditView.as_view(), name='edit-global-draw'),
    path('draws/company/<int:pk>/', views.CompanyDrawEditView.as_view(), name='edit-company-draw'),
    path('draws/history/', views.DrawHistoryAndWinnersView.as_view(), name='draw history and winners'),
    path('active-company-draws/', views.CompanyDrawListView.as_view(), name='active-company-draw-list'),
    path('active-global-draws/', views.GetAllGlobalView.as_view(), name='active-global-draw-list'),
    path('active-league/company/', views.CompanyActiveLeagueView.as_view(), name='company-active-league'),
    path('active-league/global/', views.GlobalActiveLeagueView.as_view(), name='global-active-league'),
    path('company-draws/', views.CompanyPastDrawsAPIView.as_view(), name='company-draws'),
    path('global-draws/', views.GlobalPastDrawsAPIView.as_view(), name='global-draws'),
    path('league-levels/', views.ApprovedLeaguesView.as_view(), name='approved-league-levels'),
    path('profile/<int:id>/', views.PublicUserProfileView.as_view(), name='public-user-profile'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('follow/<int:user_id>/', views.FollowToggleAPIView.as_view(), name='follow-toggle'),
    path('clap/<int:feed_id>/', views.ClapToggleAPIView.as_view(), name='clap-toggle'),
    path('following-feed/', views.FeedListView.as_view(), name='following-feed-list'),
    path('company-feed/', views.CompanyFeedListView.as_view(), name='company-feed-list'),
    path('user-gem-status/', views.UserGemStatusView.as_view(), name='user-gem-status'),
    path('league/global/status/', views.GlobalLeagueStatusView.as_view(), name='custom-user-league-status'),
    path('league/company/status/', views.CompanyLeagueStatusView.as_view(), name='custom-user-company-league-status'),
    path('company/dashboard/', views.CompanyDashboardView.as_view(), name='company-dashboard'),
    path('notifications/', views.NotificationsView.as_view(), name='notifications-list'),
    path("company/", views.CompanyListView.as_view(), name='company-list'),
    path("company/<int:pk>/", views.CompanyDetailView.as_view(), name='company-detail'),
    path("company/<int:company_id>/employees/", views.EmployeeByCompanyModelView.as_view(), name='employee-by-company'),
    path("company/<int:company_id>/employees/<int:pk>/", views.EmployeeByCompanyModelDetailsView.as_view(), name='employee-details-by-company'),
    path("employees/", views.EmployeeListView.as_view(), name='employee-list'),
    path("company/<int:pk>/employees-invitations/", views.CompanyEmployeeInvitationsListView.as_view(), name='employee-invitation-list-by-company'),
    path('global-stats/', views.GlobalStats.as_view(), name="global-stats"),
    path("global-xp-graphs/", views.GlobalXpGraph.as_view(), name="global-xp-graphs"),
    path("user/<int:user_id>/xp-stats/", views.XpStatsByUser.as_view(), name="user-xp-stats"),
    path('user-feed/', views.UserFeedView.as_view(), name='user-feed'),
    path('', include(router.urls)),
]
