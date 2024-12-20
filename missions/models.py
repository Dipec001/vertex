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

    def __str__(self):
        return f'{self.user.username} - {self.task_type.get_name_display()}'

    def complete_task(self):
        self.is_completed = True
        self.completed_date = now()
        self.save()