import pytz
from datetime import datetime
from django.core.management.base import BaseCommand
from myapp.models import WorkoutActivity, CustomUser
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

                    # Fetch all WorkoutActivity records for the user
                    workout_activities = WorkoutActivity.objects.filter(user=user)

                    for activity in workout_activities:
                        # Convert start_datetime and end_datetime to user's local time
                        start_utc_time = activity.start_datetime  # UTC start time
                        end_utc_time = activity.end_datetime  # UTC end time

                        local_start_time = start_utc_time.astimezone(user_timezone)  # Convert to local start time
                        local_end_time = end_utc_time.astimezone(user_timezone)  # Convert to local end time

                        # Update the activity with the new local timestamps
                        activity.start_datetime = local_start_time
                        activity.end_datetime = local_end_time
                        activity.save()

                    print(f"Converted timestamps for user: {user.username}")

                except IntegrityError as e:
                    print(f"Error converting timestamps for user: {user.username} - IntegrityError: {str(e)}")
                except Exception as e:
                    print(f"Error converting timestamps for user: {user.username} - {str(e)}")
