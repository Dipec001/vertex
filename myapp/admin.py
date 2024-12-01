from django.contrib import admin
from .models import (CustomUser, Company, Membership, Invitation, Xp, Streak, WorkoutActivity, DailySteps, 
                     Purchase, Prize, Draw, DrawEntry, DrawWinner, League, LeagueInstance, UserLeague, Clap,
                       UserFollowing, Feed, Gem)
# Register your models here.

# Customizing the display and functionality of the CustomUser model in the admin interface
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id','email', 'username', 'is_company_owner', 'login_type', 'date_joined', 'streak','xp')  # Fields to display in the list view
    search_fields = ('email', 'username')  # Search by email and username
    list_filter = ('is_company_owner', 'login_type', 'date_joined')  # Filter options in the sidebar
    ordering = ('email',)  # Ordering of the list
    list_per_page = 20  # Pagination to limit results per page


# Customizing the display and functionality of the Company model in the admin interface
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'owner', 'domain', 'created_at')  # Fields to display in the list view
    search_fields = ('name', 'owner__email', 'domain')  # Search by company name, owner's email, and domain
    list_filter = ('created_at',)  # Filter options in the sidebar
    ordering = ('name',)  # Ordering of the list
    list_per_page = 20  # Pagination to limit results per page


# Customizing the display and functionality of the Membership model in the admin interface
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'joined_at')  # Fields to display in the list view
    search_fields = ('user__email', 'company__name', 'role')  # Search by user email, company name, and role
    list_filter = ('role', 'joined_at')  # Filter options in the sidebar
    ordering = ('company', 'user')  # Ordering of the list
    list_per_page = 20  # Pagination to limit results per page


# Customizing the display and functionality of the Invitation model in the admin interface
@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'company', 'status', 'invite_code', 'date_sent', 'invited_by')  # Fields to display in the list view
    search_fields = ('email', 'company__name', 'invite_code')  # Search by email, company name, and invite code
    list_filter = ('status', 'date_sent')  # Filter options in the sidebar
    ordering = ('date_sent', 'email')  # Ordering of the list
    list_per_page = 20  # Pagination to limit results per page



# Customizing the display and functionality of the Xp model in the admin interface
@admin.register(Xp)
class XpAdmin(admin.ModelAdmin):
    list_display = ('user', 'totalXpToday', 'totalXpAllTime', 'gems_awarded', 'timeStamp')
    search_fields = ('user__email', 'totalXpToday', 'totalXpAllTime')
    list_filter = ('gems_awarded', 'timeStamp')
    ordering = ('user', 'timeStamp')
    list_per_page = 20

# Customizing the display and functionality of the Streak model in the admin interface
@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'currentStreak', 'highestStreak', 'timeStamp')
    search_fields = ('user__email', 'currentStreak', 'highestStreak')
    list_filter = ('timeStamp',)
    ordering = ('user', 'timeStamp')
    list_per_page = 20

# Customizing the display and functionality of the DailySteps model in the admin interface
@admin.register(DailySteps)
class DailyStepsAdmin(admin.ModelAdmin):
    list_display = ('user', 'step_count', 'xp', 'date', 'timestamp')
    search_fields = ('user__email', 'step_count', 'date')
    list_filter = ('date', 'timestamp')
    ordering = ('user', 'date')
    list_per_page = 20

# Customizing the display and functionality of the WorkoutActivity model in the admin interface
@admin.register(WorkoutActivity)
class WorkoutActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_name', 'activity_type', 'duration', 'xp', 'start_datetime')
    search_fields = ('user__email', 'activity_name', 'activity_type')
    list_filter = ('activity_type', 'start_datetime')
    ordering = ('user', 'start_datetime')
    list_per_page = 20

# Customizing the display and functionality of the Purchase model in the admin interface
@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_name', 'quantity', 'gem_used', 'timestamp')
    search_fields = ('user__email', 'item_name')
    list_filter = ('item_name', 'timestamp')
    ordering = ('user', 'timestamp')
    list_per_page = 20

# Customizing the display and functionality of the Prize model in the admin interface
@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'quantity', 'draw')
    search_fields = ('name', 'draw__draw_name')
    list_filter = ('value',)
    ordering = ('name', 'value')
    list_per_page = 20

# Customizing the display and functionality of the Draw model in the admin interface
@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
    list_display = ('id', 'draw_name', 'draw_type', 'draw_date', 'number_of_winners', 'is_active')
    search_fields = ('draw_name', 'company__name', 'draw_type')
    list_filter = ('draw_type', 'draw_date', 'is_active')
    ordering = ('draw_date', 'draw_name')
    list_per_page = 20

# Customizing the display and functionality of the DrawEntry model in the admin interface
@admin.register(DrawEntry)
class DrawEntryAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'draw', 'timestamp')
    search_fields = ('user__email', 'draw__draw_name')
    list_filter = ('timestamp',)
    ordering = ('draw', 'user')
    list_per_page = 20

# Customizing the display and functionality of the DrawWinner model in the admin interface
@admin.register(DrawWinner)
class DrawWinnerAdmin(admin.ModelAdmin):
    list_display = ('id' ,'user', 'prize', 'draw', 'win_date')
    search_fields = ('user__email', 'prize__name', 'draw__draw_name')
    list_filter = ('win_date',)
    ordering = ('win_date', 'user')
    list_per_page = 20


# Customizing the display and functionality of the League model in the admin interface
@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order')  # Display League ID, name, and order
    search_fields = ('name',)  # Search by league name
    ordering = ('order',)  # Order by ranking
    list_per_page = 20  # Pagination

# Customizing the display and functionality of the LeagueInstance model in the admin interface
@admin.register(LeagueInstance)
class LeagueInstanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'league', 'league_start', 'league_end', 'company', 'max_participants')  # Fields to display
    search_fields = ('id','league__name', 'company__name')  # Search by league name
    list_filter = ('company', 'league_start', 'league_end', 'is_active')  # Filter options
    ordering = ('league_start',)  # Ordering of the list
    list_per_page = 20  # Pagination

# Customizing the display and functionality of the UserLeague model in the admin interface
@admin.register(UserLeague)
class UserLeagueAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'league_instance', 'xp_company','xp_global', 'is_retained')  # Fields to display
    search_fields = ('id','user__username', 'league_instance__league__name')  # Search by user and league
    list_filter = ('is_retained',)  # Filter by retention status
    ordering = ('user', 'league_instance')  # Order by user and league
    list_per_page = 20  # Pagination


@admin.register(UserFollowing)
class UserFollowingAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'followed_at')  # Display these fields in the list view
    search_fields = ('follower__username', 'following__username')  # Allow search by follower and following usernames
    list_filter = ('followed_at',)  # Filter by the date the follow occurred
    ordering = ('-followed_at',)  # Ordering by the most recent follow first
    list_per_page = 20  # Pagination, 20 entries per page


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'created_at', 'claps_count')  # Fields to display in the list
    search_fields = ('user__username', 'content')  # Allow searching by username and feed content
    list_filter = ('created_at',)  # Filter by creation date
    ordering = ('-created_at',)  # Ordering by the most recent feed first
    list_per_page = 20  # Pagination, 20 entries per page


@admin.register(Clap)
class ClapAdmin(admin.ModelAdmin):
    list_display = ('user', 'feed', 'created_at')  # Display user, feed, and timestamp
    search_fields = ('user__username', 'feed__content')  # Search by user username and feed content
    list_filter = ('created_at',)  # Filter by creation date of the clap
    ordering = ('-created_at',)  # Ordering by the most recent clap first
    list_per_page = 20  # Pagination, 20 entries per page


@admin.register(Gem)
class GemAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'xp_gem', 'manual_gem','copy_xp_gem','copy_manual_gem']
    list_filter = ['user', 'date']
    search_fields = ['user__email']

