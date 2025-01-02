from typing import Literal

from django.db.models import Sum

from myapp.models import Xp, DailySteps
from myapp.utils import get_date_range


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
    return daily_stats


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


def get_daily_steps_and_xp(company, interval: Literal["this_week", "this_month", "last_week"]):
    daily_stats = []
    for single_date in get_date_range(interval):
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
