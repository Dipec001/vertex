import sys
from django.core.management.base import BaseCommand
from myapp.models import LeagueInstance

class Command(BaseCommand):
    help = 'Bulk delete the first 20,000 oldest LeagueInstance records'

    def handle(self, *args, **kwargs):
        # Fetch the IDs of the first 20,000 oldest LeagueInstance records
        league_instance_ids = LeagueInstance.objects.order_by('league_start').values_list('id', flat=True)[:24000]

        # Confirm the deletion
        confirm = input(f'Are you sure you want to delete {len(league_instance_ids)} LeagueInstance records? [yes/no]: ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Aborted.'))
            sys.exit()

        # Perform the bulk deletion
        deleted_count, _ = LeagueInstance.objects.filter(id__in=league_instance_ids).delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} LeagueInstance records.'))
