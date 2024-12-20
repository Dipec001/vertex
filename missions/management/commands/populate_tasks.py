# populate_tasks.py

from django.core.management.base import BaseCommand
from missions.models import TaskType
from missions.choices import DEFAULT_TASKS

class Command(BaseCommand):
    help = 'Populates the database with predefined task types'

    def handle(self, *args, **kwargs):
        for task_data in DEFAULT_TASKS:
            TaskType.objects.get_or_create(name=task_data['name'], defaults={'gem_value': task_data['gem_value']})
        self.stdout.write(self.style.SUCCESS('Successfully populated task types'))
