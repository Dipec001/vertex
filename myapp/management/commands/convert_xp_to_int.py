from django.core.management.base import BaseCommand
from django.db.models import Count
from myapp.models import Xp, DailySteps, WorkoutActivity

class Command(BaseCommand):
    help = 'Convert XP fields from float to int and clean duplicates'

    def handle(self, *args, **kwargs):
        # Convert XP fields from float to int
        self.convert_xp_fields()

        # Remove duplicate WorkoutActivity records
        self.remove_duplicates()

    def convert_xp_fields(self):
        for xp in Xp.objects.all():
            xp.totalXpToday = int(xp.totalXpToday)
            xp.totalXpAllTime = int(xp.totalXpAllTime)
            xp.save()
        self.stdout.write(self.style.SUCCESS('Successfully converted XP fields in Xp model to integer'))

        for steps in DailySteps.objects.all():
            steps.xp = int(steps.xp)
            steps.save()
        self.stdout.write(self.style.SUCCESS('Successfully converted XP fields in DailySteps model to integer'))

        for activity in WorkoutActivity.objects.all():
            activity.xp = int(activity.xp)
            activity.save()
        self.stdout.write(self.style.SUCCESS('Successfully converted XP fields in WorkoutActivity model to integer'))

    def remove_duplicates(self):
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
