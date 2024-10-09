from celery import shared_task
from .email_utils import send_invitation_email
from django.utils import timezone
from .models import Streak, CustomUser, Xp
from django.db.models import Sum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)  # You can adjust the logging level as needed
logger = logging.getLogger(__name__)



@shared_task
def send_invitation_email_task(invite_code, company_name, inviter_name, to_email):
    return send_invitation_email(invite_code, company_name, inviter_name, to_email)


@shared_task
def reset_daily_streaks():
    # Fetch users who earned less than 500 XP for today
    current_utc_time = timezone.now()
    
    # Fetch users in batches
    batch_size = 100  # Adjust based on your needs
    offset = 0

    while True:
        users = CustomUser.objects.exclude(timezone=None)[offset:offset + batch_size]
        if not users:
            logger.info("Processed all users successfully.")  # Log when no more users are left
            break  # Exit if no more users

        for user in users:
            # Get the current time in the user's timezone
            local_now = current_utc_time.astimezone(user.timezone)

            # Define today's start and end in user's local time
            today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timezone.timedelta(days=1)

            # Get the user's XP for today
            daily_xp = Xp.objects.filter(user=user, timeStamp__range=(today_start, today_end)).aggregate(total_xp=Sum('totalXpToday'))['total_xp'] or 0

            # Only reset the streak if today's XP is less than 500
            if daily_xp < 500:
                streak_record, _ = Streak.objects.get_or_create(user=user)
                streak_record.currentStreak = 0
                streak_record.save()

        offset += batch_size  # Move to the next batch
