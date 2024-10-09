from django.contrib import admin
from .models import CustomUser, Company, Membership, Invitation, Xp, Streak, WorkoutActivity
# Register your models here.

# Customizing the display and functionality of the CustomUser model in the admin interface
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'is_company_owner', 'login_type', 'date_joined', 'streak', 'tickets', 'xp')  # Fields to display in the list view
    search_fields = ('email', 'username')  # Search by email and username
    list_filter = ('is_company_owner', 'login_type', 'date_joined')  # Filter options in the sidebar
    ordering = ('email',)  # Ordering of the list
    list_per_page = 20  # Pagination to limit results per page


# Customizing the display and functionality of the Company model in the admin interface
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'domain', 'created_at')  # Fields to display in the list view
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


admin.site.register(Xp)
admin.site.register(Streak)
admin.site.register(WorkoutActivity)