import pytz
from datetime import datetime
from django.core.management.base import BaseCommand
from myapp.models import Xp, CustomUser
from django.db import transaction, IntegrityError

class Command(BaseCommand):
    help = 'Convert all UTC XP timestamps to the users\' local time'

    def handle(self, *args, **kwargs):
        self.convert_utc_to_local()

    def convert_utc_to_local(self):
        # Fetch all users
        users = CustomUser.objects.all()

        with transaction.atomic():
            for user in users:
                try:
                    user_timezone = pytz.timezone(user.timezone.key)  # Get user's timezone

                    # Fetch all XP records for the user
                    xp_records = Xp.objects.filter(user=user)

                    for record in xp_records:
                        utc_time = record.timeStamp  # UTC timestamp
                        local_time = utc_time.astimezone(user_timezone)  # Convert to local time
                        local_date = local_time.date()  # Extract local date

                        # Update the record with the new local timestamp and date
                        record.timeStamp = local_time
                        record.date = local_date
                        record.save()

                    print(f"Converted XP timestamps for user: {user.username}")

                except IntegrityError as e:
                    print(f"Error converting XP timestamps for user: {user.username} - IntegrityError: {str(e)}")
                except Exception as e:
                    print(f"Error converting XP timestamps for user: {user.username} - {str(e)}")
