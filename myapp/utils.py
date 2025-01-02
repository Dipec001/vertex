import calendar
from datetime import datetime, timedelta
from typing import Literal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Sum
from django.utils import timezone

from myapp.models import DailySteps, Gem, Xp


def send_user_notification(user, notif):
    """
    Sends a WebSocket notification to a specific user.

    Args:
        user: The User instance to send the notification to.
        notif: The Notification instance containing the details.
    """
    channel_layer = get_channel_layer()

     # Get the user's timezone; default to UTC if not set
    user_timezone = user.timezone
    print(user_timezone, 'user timezone')

    # Convert the created_at timestamp to the user's local timezone
    user_local_time = notif.created_at.astimezone(user_timezone)
    print(user_local_time, 'user local time')

    async_to_sync(channel_layer.group_send)(
        f'notifications_{user.id}',
        {
            'type': 'send_notification',
            'data': {
                'id': notif.id,
                'notif_type': notif.notif_type,
                'content': notif.content,
                'created_at': user_local_time.isoformat()
            }
        }
    )


def add_manual_gem(user, manual_gem_count, date):
    gem, created = Gem.objects.get_or_create(user=user, date=date)
    # Ensure manual_gem is not None before adding
    if gem.manual_gem is None:
        gem.manual_gem = 0  # Initialize to 0 if it's None
    gem.manual_gem += manual_gem_count  # Increment the manual gems
    gem.copy_manual_gem += manual_gem_count
    gem.save()
    
def get_global_xp_for_stats_by_user(user_id, interval: Literal["this_week", "this_month", "last_week"]):
    daily_stats = []
    for single_date in get_date_range(interval):
        # Get all XP or this date
        daily_xp = Xp.objects.filter(
            date=single_date,
            user_id=user_id,
        ).aggregate(
            total_xp=Sum('totalXpToday')
        )['total_xp'] or 0

        daily_stats.append({
            'date': single_date,
            'total_xp': daily_xp
        })

def get_global_xp_for_stats(interval: Literal["this_week", "this_month", "last_week"]):
    daily_stats = []
    for single_date in get_date_range(interval):
        # Get all XP or this date
        daily_xp = Xp.objects.filter(
            date=single_date
        ).aggregate(
            total_xp=Sum('totalXpToday')
        )['total_xp'] or 0

        daily_stats.append({
            'date': single_date,
            'total_xp': daily_xp
        })
    return daily_stats

def get_last_day_and_first_day_of_this_month():
    """
    Calculate the first and last day of the current month.

    This function determines the first and last day of the current month
    based on the current date.

    Returns:
        tuple: A tuple containing two datetime objects:
            - The first element is the first day of the current month.
            - The second element is the last day of the current month.
    """
    # Get the current date
    today = datetime.now()

    # Get the first day and the number of days in the current month
    first_day_of_month = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)

    # Get the last day of the month
    last_day_of_month = first_day_of_month.replace(day=last_day)

    return first_day_of_month, last_day_of_month

def get_daily_steps_and_xp(company, interval: Literal["this_week", "this_month", "last_week"]):
    daily_stats = []
    for single_date in get_date_range("this_month"):
        # Get steps for this date
        daily_steps = DailySteps.objects.filter(
            user__membership__company=company,
            date=single_date
        ).aggregate(
            total_steps=Sum('step_count')
        )['total_steps'] or 0

        # Get XP for this date
        daily_xp = Xp.objects.filter(
            user__membership__company=company,
            date=single_date
        ).aggregate(
            total_xp=Sum('totalXpToday')
        )['total_xp'] or 0

        daily_stats.append({
            'date': single_date,
            'total_steps': daily_steps,
            'total_xp': daily_xp
        })
        
    return daily_stats



def get_date_range(interval: Literal["this_week", "this_month", "last_week"]):
    """
    Generate a list of dates for a specified time interval.

    This function returns a list of dates based on the given interval,
    which can be 'this_week', 'this_month', or 'last_week'.

    Parameters:
    interval (str): The time interval for which to generate dates.
                    Valid options are:
                    - 'this_week': Current week (Monday to Sunday)
                    - 'this_month': All days in the current month
                    - 'last_week': Previous week (Monday to Sunday)

    Returns:
    list: A list of datetime.date objects representing the dates in the specified interval.

    Raises:
    ValueError: If an invalid interval is provided.

    """
    today = datetime.now().date()

    if interval == "this_week":
        # Start of the current week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        dates = [start_of_week + timedelta(days=i) for i in range(7)]

    elif interval == "this_month":
        # Start and end of the current month
        start_of_month = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end_of_month = today.replace(day=last_day)
        dates = [start_of_month + timedelta(days=i) for i in range((end_of_month - start_of_month).days + 1)]

    elif interval == "last_week":
        # Start of the last week (Monday)
        start_of_last_week = today - timedelta(days=today.weekday() + 7)
        dates = [start_of_last_week + timedelta(days=i) for i in range(7)]

    else:
        raise ValueError("Invalid interval. Choices are: 'this_week', 'this_month', 'last_week'.")

    return dates