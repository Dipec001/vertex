import sys
from django.core.management.base import BaseCommand
from myapp.models import LeagueInstance

class Command(BaseCommand):
    help = 'Bulk delete the first 20,000 oldest LeagueInstance records'

    def handle(self, *args, **kwargs):
        # Fetch the first 20,000 oldest LeagueInstance records
        league_instances = LeagueInstance.objects.order_by('league_start')[:20000]

        # Confirm the deletion
        confirm = input(f'Are you sure you want to delete {league_instances.count()} LeagueInstance records? [yes/no]: ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Aborted.'))
            sys.exit()

        # Perform the deletion
        deleted_count, _ = league_instances.delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} LeagueInstance records.'))
