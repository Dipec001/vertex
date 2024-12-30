from datetime import timedelta
from myapp.models import DailySteps, Gem, Xp
from django.db.models import Sum
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


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
    
def get_last_30_days(today):
    """
    Generate a list of dates for the last 30 days, including today.
    
    Args:
        today: datetime.date - The reference date to count back from
        
    Returns:
        list[datetime.date]: List of 30 dates, starting from today going backwards
        
    Example:
        If today is 2024-03-20, returns dates from 2024-03-20 to 2024-02-20
    """
    dates = []
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        dates.append(date)
    return dates

def get_global_xp_for_stats_for_last_30_days_by_user(user_id):
    daily_stats = []
    today = timezone.now()
    for single_date in get_last_30_days(today):
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

def get_global_xp_for_stats_for_last_30_days(today):
    daily_stats = []
    for single_date in get_last_30_days(today):
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
def get_daily_steps_and_xp(company, today):
    daily_stats = []
    for single_date in get_last_30_days(today):
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

