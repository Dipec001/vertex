from django.core.management.base import BaseCommand
from celery import Celery
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Purge old Celery tasks'

    def handle(self, *args, **kwargs):
        from vertex.celery import app

        try:
            purged_count = app.control.purge()
            self.stdout.write(self.style.SUCCESS(f'Successfully purged {purged_count} tasks'))
            logger.info(f'Purged {purged_count} tasks from Celery queue')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error purging tasks: {e}'))
            logger.error(f'Error purging tasks: {e}')
