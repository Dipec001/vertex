# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserTask, TaskType
from myapp.models import DailySteps, Streak, WorkoutActivity
from django.utils.timezone import now
from django.db.models import Sum

## TODO: Check for time conversion before the if statement of checking instance.date to the now()

MAX_STEP = 1000
MEDITATION_DURATION = 10
RUN_DISTANCE = 3

@receiver(post_save, sender=DailySteps)
def update_task_progress(sender, instance, **kwargs):
    """ Update the step daily task progress"""
    user = instance.user
    step_count = instance.step_count
    print(step_count, 'step count today')
    today = instance.date

    if instance.date != now().date():
        return

    # Update the task progress
    try:
        step_task_type = TaskType.objects.get(name='steps')
        user_task= UserTask.objects.get(user=user, task_type=step_task_type, created_at__date=today)
        if user_task.is_completed:
            return
        
        # Recalculate progress
        total_steps_today = step_count
        user_task.progress = min(total_steps_today, MAX_STEP)  # Assuming 1000 is the max step count for the task
        if total_steps_today >= MAX_STEP:
            user_task.complete_task()
        else:
            user_task.save()
    except TaskType.DoesNotExist:
        print("TaskType 'steps' does not exist")
    except UserTask.DoesNotExist:
        print("No UserTask for today's steps")


@receiver(post_save, sender=Streak)
def update_streak_task(sender, instance, **kwargs):
    """ Update the streak task progress """
    user = instance.user
    today = instance.date

    if instance.date != now().date():
        return

    # Update the streak task progress
    try:
        streak_task_type = TaskType.objects.get(name='streak')
        user_task = UserTask.objects.get(user=user, task_type=streak_task_type, created_at__date=today)
        if user_task.is_completed:
            return
        
        # Assuming a streak is completed by updating the streak record for the day
        user_task.progress = 1
        user_task.complete_task()
    except TaskType.DoesNotExist:
        print("TaskType 'streak' does not exist")
    except UserTask.DoesNotExist:
        print("No UserTask for today's streak task")


@receiver(post_save, sender=WorkoutActivity)
def update_workout_tasks(sender, instance, **kwargs):
    """Update the meditation and running task progress."""
    user = instance.user
    duration = instance.duration
    distance = instance.distance
    today = instance.start_datetime.date()

    if instance.start_datetime.date() != now().date():
        return

    if instance.activity_type == "mindfulness" and instance.metadata.lower() == "meditation":
        print('mindfulness')
        try:
            meditation_task_type = TaskType.objects.get(name='meditation')
            user_task = UserTask.objects.get(user=user, task_type=meditation_task_type, created_at__date=today)
            if user_task.is_completed:
                return
            
            user_task.progress = min(user_task.progress + duration, MEDITATION_DURATION)
            
            if user_task.progress >= MEDITATION_DURATION:
                user_task.complete_task()
            else:
                user_task.save()
        except TaskType.DoesNotExist:
            print("TaskType 'meditation' does not exist")
        except UserTask.DoesNotExist:
            print("No UserTask for today's meditation task")

    if instance.activity_type == "movement" and instance.activity_name.lower() == "running":
        print('running')
        try:
            running_task_type = TaskType.objects.get(name='run')
            user_task = UserTask.objects.get(user=user, task_type=running_task_type, created_at__date=today)
            if user_task.is_completed:
                return

            user_task.progress = min(user_task.progress + distance, RUN_DISTANCE)
            
            if user_task.progress >= RUN_DISTANCE:
                user_task.complete_task()
            else:
                user_task.save()
        except TaskType.DoesNotExist:
            print("TaskType 'run' does not exist")
        except UserTask.DoesNotExist:
            print("No UserTask for today's running task")


