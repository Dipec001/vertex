from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from myapp.models import Notif, CustomUser
from django.utils import timezone

class Command(BaseCommand):
    help = "Generate 50 or 60 identical mock notifications for a specified user."

    def handle(self, *args, **options):
        
        # Fetch the user with ID 9
        try:
            user = CustomUser.objects.get(id=9)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR("User with ID 9 does not exist."))
            return

        # Notification details
        notif_type = "purchase_companydraw"
        content = "You converted 2 gems into 2 company draw tickets."

        # Number of notifications to create (set to 60)
        num_notifications = 60

        # Create the notifications
        notifications = []
        for _ in range(num_notifications):
            notif = Notif(
                user=user,
                notif_type=notif_type,
                content=content,
                created_at=timezone.now()
            )
            notifications.append(notif)

        # Bulk create notifications
        Notif.objects.bulk_create(notifications)

        self.stdout.write(self.style.SUCCESS(f"Successfully created {num_notifications} mock notifications for user with ID 9."))
