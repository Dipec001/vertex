# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserTask
from django.utils.timezone import now
from django.db import transaction
from myapp.utils import add_manual_gem


class ActiveTasksView(APIView):
    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone).date()

        active_tasks = UserTask.objects.filter(user=user, created_at__date=user_local_time, is_claimed=False)
        completed_tasks = UserTask.objects.filter(user=user, created_at__date=user_local_time, is_completed=True, is_claimed=True)
        
        total_completed_tasks = completed_tasks.count()
        total_available_tasks = active_tasks.count()

        tasks_data = [{
            'task_id': task.id,
            'task_name': task.task_type.get_name_display(),
            'progress': task.progress_with_goal,
            'progress_percentage': task.progress_percentage_display,
            'is_completed': task.is_completed,
            'is_claimed': task.is_claimed,
            'gem_value': task.task_type.gem_value,
        } for task in active_tasks]

        response_data = { 
            'total_available_tasks': total_available_tasks, 
            'total_completed_tasks': total_completed_tasks, 
            'tasks': tasks_data 
        }

        return Response(response_data, status=status.HTTP_200_OK)



class CompletedTasksView(APIView):
    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        user_local_time = now().astimezone(user_timezone)
        completed_tasks = UserTask.objects.filter(user=user, created_at__date=user_local_time.date(), is_completed=True, is_claimed=True)
        
        total_completed_tasks = completed_tasks.count()

        tasks_data = []
        for task in completed_tasks:
            tasks_data.append({
                'task_id': task.id,
                'task_name': task.task_type.get_name_display(),
                'progress': task.progress_with_goal,
                'progress_percentage': task.progress_percentage_display,
                'is_completed': task.is_completed,
                'is_claimed': task.is_claimed,
                'gem_value': task.task_type.gem_value,
            })

        response_data = { 
            'total_completed_tasks': total_completed_tasks, 
            'tasks': tasks_data 
        }

        return Response(response_data, status=status.HTTP_200_OK)

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


class MissionsDataView(APIView):
    def get(self, request):
        user = request.user
        user_timezone = user.timezone
        user_local_date = now().astimezone(user_timezone).date()

        # Fetch user tasks for today
        user_tasks_today = UserTask.objects.filter(user=user, created_at__date=user_local_date)

        # Calculate dynamic progress for daily tasks
        total_tasks = user_tasks_today.count()
        completed_tasks = user_tasks_today.filter(is_completed=True).count()
        daily_progress = f"{completed_tasks}/{total_tasks}" if total_tasks > 0 else "0/0"

        # Construct response data
        dashboard_data = [
            {
                "title": "Company Challenges",
                "subtitle": "Your company has reached 23000 of 50000 steps",
                "progress": "52%",
            },
            {
                "title": "Journeys",
                "subtitle": "You are 32% of your way through level 1",
                "progress": "32%",
            },
            {
                "title": "Meditation",
                "subtitle": "Meditations completed this week",
                "progress": "5/7",
            },
            {
                "title": "Daily Tasks",
                "subtitle": "Your tasks available today",
                "progress": daily_progress,
            },
        ]

        return Response(dashboard_data, status=status.HTTP_200_OK)
