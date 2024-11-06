from django.core.management.base import BaseCommand
from myapp.models import League

class Command(BaseCommand):
    help = 'Populates the League model with predefined leagues and their order.'

    def handle(self, *args, **kwargs):
        leagues = [
            ('Pathfinder league', 1),
            ('Discoverer league', 2),
            ('Explorer league', 3),
            ('Voyageur league', 4),
            ('Navigator league', 5),
            ('Pioneer league', 6),
            ('Adventurer league', 7),
            ('Expedition league', 8),
            ('Conqueror league', 9),
            ('Champion league', 10),
        ]

        for name, order in leagues:
            league, created = League.objects.get_or_create(name=name, defaults={'order': order})
            if created:
                self.stdout.write(self.style.SUCCESS(f'League "{name}" created with order {order}.'))
            else:
                self.stdout.write(self.style.WARNING(f'League "{name}" already exists.'))

        self.stdout.write(self.style.SUCCESS('League model populated successfully.'))
