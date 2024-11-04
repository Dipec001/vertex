from django.core.management.base import BaseCommand
from myapp.models import WorkoutActivity
from django.db.models import Count

class Command(BaseCommand):
    help = 'Remove duplicate WorkoutActivity records'

    def handle(self, *args, **kwargs):
        duplicates = WorkoutActivity.objects.values(
            'user_id', 'start_datetime'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)

        for duplicate in duplicates:
            activities = WorkoutActivity.objects.filter(
                user_id=duplicate['user_id'],
                start_datetime=duplicate['start_datetime']
            ).order_by('id')

            # Keep the first occurrence and delete the rest
            for activity in activities[1:]:
                activity.delete()

        self.stdout.write(self.style.SUCCESS('Successfully removed duplicate WorkoutActivity records'))
