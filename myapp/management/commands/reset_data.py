from django.core.management.base import BaseCommand
from django.db import connection
from myapp.models import Xp, Streak, DailySteps, WorkoutActivity, Purchase, CustomUser

class Command(BaseCommand):
    help = 'Reset all specified data and reset certain fields in CustomUser'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting the reset process...')
        self.truncate_tables()
        self.reset_custom_user_fields()
        self.stdout.write(self.style.SUCCESS('Data reset successfully.'))

    def truncate_tables(self):
        with connection.cursor() as cursor:
            # Truncate the specified tables
            tables = [Xp, Streak, DailySteps, WorkoutActivity, Purchase]
            for table in tables:
                cursor.execute(f'TRUNCATE TABLE {table._meta.db_table} RESTART IDENTITY CASCADE')
                self.stdout.write(f'Table {table._meta.db_table} truncated.')

    def reset_custom_user_fields(self):
        # Reset specified fields in CustomUser
        CustomUser.objects.update(
            streak=0,
            company_tickets=0,
            global_tickets=0,
            streak_savers=0,
            xp=0,
            gem=0,
            gems_spent=0
        )
        self.stdout.write('CustomUser fields reset.')
