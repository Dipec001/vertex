# models.py
from django.conf import settings
from django.db import models
from .choices import TASK_CHOICES
from django.utils.timezone import now

class TaskType(models.Model):
    name = models.CharField(max_length=100, choices=TASK_CHOICES, unique=True)
    gem_value = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.get_name_display()} - {self.gem_value} gems"

class UserTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task_type = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    is_claimed = models.BooleanField(default=False)  # New field to track claim status

    TASK_GOALS = { 
        'steps': 1000, 
        'swim': 10, 
        'run': 3, 
        'streak': 1, 
        'meditation': 10, 
    }

    def __str__(self):
        return f'{self.user.username} - {self.task_type.get_name_display()}'

    def complete_task(self):
        self.is_completed = True
        self.completed_date = now()
        self.save()


    def progress_percentage(self): 
        goal = self.TASK_GOALS.get(self.task_type.name, 1) 
        return min(100, int((self.progress / goal) * 100)) 
    
    @property 
    def progress_with_goal(self): 
        goal = self.TASK_GOALS.get(self.task_type.name, 1) 
        return f"{self.progress}/{goal}" 
    
    @property 
    def progress_percentage_display(self): 
        return f"{self.progress_percentage()}%"