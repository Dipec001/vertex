from django.contrib import admin
from .models import SupportTicket, SupportMessage

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'user__username')
    list_filter = ('created_at', 'updated_at')

@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'is_current_user', 'message_time', 'support_staff_name')
    search_fields = ('message', 'support_staff_name', 'ticket__title')
    list_filter = ('message_time', 'is_current_user')
