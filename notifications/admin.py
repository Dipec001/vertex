from django.contrib import admin
from .models import PushNotificationStatus

class PushNotificationStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'sent', 'last_sent')
    search_fields = ('user__email', 'notification_type')

admin.site.register(PushNotificationStatus, PushNotificationStatusAdmin)
