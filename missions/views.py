# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserTask, TaskType
from django.utils.timezone import now
from django.db import transaction
from myapp.models import Gem
from myapp.utils import add_manual_gem

## TODO: Use serialization here 👇

class ActiveTasksView(APIView):
    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone).date()

        active_tasks = UserTask.objects.filter(user=user, created_at__date=user_local_time, is_claimed=False)
        tasks_data = [{
            'task_id': task.id,
            'task_name': task.task_type.get_name_display(),
            'progress': task.progress,
            'is_completed': task.is_completed,
            'is_claimed': task.is_claimed,
            'gem_value': task.task_type.gem_value,
        } for task in active_tasks]

        return Response(tasks_data, status=status.HTTP_200_OK)


class CompletedTasksView(APIView):
    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone)
        completed_tasks = UserTask.objects.filter(user=user, created_at=user_local_time, is_completed=True, is_claimed=True)
        
        tasks_data = []
        for task in completed_tasks:
            tasks_data.append({
                'task': task.task_type.get_name_display(),
                'progress': task.progress,
                'completed_date': task.completed_date,
                'gem_value': task.task_type.gem_value,
            })

        return Response(tasks_data, status=status.HTTP_200_OK)

class ClaimTaskView(APIView):
    def post(self, request, task_id):
        user = request.user
        try:
            task = UserTask.objects.get(id=task_id, user=request.user)
            if task.is_completed and not task.is_claimed:
                task.is_claimed = True
                task.save()

                # Add gems to user's gem balance
                add_manual_gem(user=user, manual_gem_count=task.task_type.gem_value, date=now().date())

                return Response({'message': 'Task\'s gems claimed successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Task is not eligible for claiming gems'}, status=status.HTTP_400_BAD_REQUEST)
        except UserTask.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
