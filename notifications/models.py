from django.db import models
from django.conf import settings

# Create your models here.

class PushNotificationStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50)
    sent = models.BooleanField(default=False)
    last_sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} - {self.notification_type} - Sent: {self.sent}'
