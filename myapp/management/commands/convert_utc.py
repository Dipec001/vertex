import pytz
from datetime import datetime
from django.core.management.base import BaseCommand
from myapp.models import DailySteps, CustomUser
from django.db import transaction, IntegrityError

class Command(BaseCommand):
    help = 'Convert all UTC timestamps to the users\' local time'

    def handle(self, *args, **kwargs):
        self.convert_utc_to_local()

    def convert_utc_to_local(self):
        # Fetch all users
        users = CustomUser.objects.all()

        with transaction.atomic():
            for user in users:
                try:
                    user_timezone = pytz.timezone(user.timezone.key)  # Get user's timezone

                    # Fetch all DailySteps records for the user
                    daily_steps_records = DailySteps.objects.filter(user=user)

                    for record in daily_steps_records:
                        utc_time = record.timestamp  # UTC timestamp
                        local_time = utc_time.astimezone(user_timezone)  # Convert to local time
                        local_date = local_time.date()  # Extract local date

                        # Check for existing record with the same user_id and local_date
                        existing_record = DailySteps.objects.filter(user=user, date=local_date).first()

                        if existing_record:
                            # Merge records: combine step counts and update timestamp
                            existing_record.step_count += record.step_count
                            existing_record.timestamp = max(existing_record.timestamp, local_time)
                            existing_record.save()
                            record.delete()  # Remove the old record after merging
                        else:
                            # Update the record with the new local timestamp and date
                            record.timestamp = local_time
                            record.date = local_date
                            record.save()

                    print(f"Converted timestamps for user: {user.username}")

                except IntegrityError as e:
                    print(f"Error converting timestamps for user: {user.username} - IntegrityError: {str(e)}")
                except Exception as e:
                    print(f"Error converting timestamps for user: {user.username} - {str(e)}")

