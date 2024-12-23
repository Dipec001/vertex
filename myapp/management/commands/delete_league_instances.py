import sys
from django.core.management.base import BaseCommand
from myapp.models import LeagueInstance

class Command(BaseCommand):
    help = 'Bulk delete the first 105107 oldest LeagueInstance records'

    def handle(self, *args, **kwargs):
        # Fetch the IDs of the first 105107 oldest LeagueInstance records
        league_instance_ids = list(
            LeagueInstance.objects.order_by('league_start').values_list('id', flat=True)[:105107]
        )

        if not league_instance_ids:
            self.stdout.write(self.style.WARNING('No LeagueInstance records found for deletion.'))
            return

        # Confirm the deletion
        confirm = input(f'Are you sure you want to delete {len(league_instance_ids)} LeagueInstance records? [yes/no]: ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Deletion aborted.'))
            sys.exit()

        # Perform the bulk deletion
        deleted_count, _ = LeagueInstance.objects.filter(id__in=league_instance_ids).delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} LeagueInstance records.'))
