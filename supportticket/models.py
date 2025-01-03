from django.db import models
from django.conf import settings

class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('resolved', 'Resolved'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Ticket {self.id}: {self.title}"


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    is_current_user = models.BooleanField(default=True)  # True for user, False for staff
    message = models.TextField()
    message_time = models.DateTimeField(auto_now_add=True)
    support_staff_name = models.CharField(max_length=255, default="Anytime Rewards Support")

    def __str__(self):
        return f"Message {self.id} for Ticket {self.ticket.id}"
