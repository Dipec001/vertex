# tasks.py

from celery import shared_task
from pytz import timezone
from django.utils.timezone import now
from .models import TaskType, UserTask
from myapp.models import CustomUser
import random  # Import random module

## TODO: Implement Batching
## TODO: Implement creating task the previous day to make sure it is available at the start of the day 00:01

@shared_task
def assign_daily_tasks():
    """Assigns daily tasks to users based on their local time zone."""
    task_types = TaskType.objects.all()
    users = CustomUser.objects.filter(is_superuser=False) # Exclude superusers
    current_utc_time = now()

    for user in users:
        user_timezone = user.timezone
        user_local_time = current_utc_time.astimezone(user_timezone)
        user_local_date = user_local_time.date()

        # Assign tasks if none exist for today in user's local time
        user_tasks_today = UserTask.objects.filter(user=user, created_at__date=user_local_date)
        if not user_tasks_today.exists():
            num_tasks = random.randint(3, 5)  # Randomly select between 3 and 5 tasks
            assigned_tasks = task_types.order_by('?')[:num_tasks]  # Randomly pick tasks
            UserTask.objects.bulk_create([
                UserTask(user=user, task_type=task_type, created_at=now())
                for task_type in assigned_tasks
            ])
