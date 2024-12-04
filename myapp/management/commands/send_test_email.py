# myapp/management/commands/send_test_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail

class Command(BaseCommand):
    help = 'Sends a test email'

    def handle(self, *args, **kwargs):
        send_mail(
            'Test Email',
            'This is a test email.',
            'your-email@example.com',  # Replace with your actual email
            ['recipient@example.com'],  # Replace with the recipient's email
        )
        self.stdout.write(self.style.SUCCESS('Test email sent successfully'))
