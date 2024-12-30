from django.urls import path
from . import views

urlpatterns = [
    path('active-tasks/', views.ActiveTasksView.as_view(), name='daily-tasks'),
    path('completed-tasks/', views.CompletedTasksView.as_view(), name='completed-task'),
    path('claim-task/<int:task_id>/', views.ClaimTaskView.as_view(), name='claim-task'),
    path('missions-data/', views.MissionsDataView.as_view(), name='missions-data'),
]
