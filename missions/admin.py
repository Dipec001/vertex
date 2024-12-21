from django.contrib import admin
from .models import TaskType, UserTask

@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'gem_value')
    search_fields = ('name',)

@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'task_type','created_at', 'progress', 'is_completed', 'completed_date', 'is_claimed')
    list_filter = ('is_completed', 'is_claimed', 'completed_date')
    search_fields = ('user__email', 'user__username', 'task_type__name')
