from celery import shared_task
from .email_utils import send_invitation_email
from django.utils import timezone
from .models import Streak, CustomUser, Xp, Draw, Company
from django.db.models import Sum
import logging
from datetime import timedelta, datetime
from django.utils import timezone as django_timezone
from zoneinfo import ZoneInfo  # Use ZoneInfo instead of pytz

# Configure logging
logging.basicConfig(level=logging.INFO)  # You can adjust the logging level as needed
logger = logging.getLogger(__name__)



@shared_task
def send_invitation_email_task(invite_code, company_name, inviter_name, to_email):
    return send_invitation_email(invite_code, company_name, inviter_name, to_email)

@shared_task
def reset_daily_streaks():
    # Batch size for processing users
    batch_size = 100  # Adjust based on your needs
    offset = 0

    while True:
        # Fetch users who have a timezone set and whose current streak is greater than 0
        users = CustomUser.objects.exclude(timezone=None).filter(
            streak_records__currentStreak__gt=0
        )[offset:offset + batch_size]
        
        if not users:  # Exit if no more users are left
            logger.info("Processed all users successfully.")
            break

        for user in users:
            # Get the current time in the user's timezone
            current_utc_time = timezone.now()
            user_local_time = current_utc_time.astimezone(user.timezone)

            # Check if the current time is midnight in the user's local time
            if user_local_time.hour == 0 and user_local_time.minute < 60:
                print(True)
                # Define yesterday's start and end times in UTC
                yesterday_start = user_local_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                yesterday_end = yesterday_start + timedelta(days=1)

                # Retrieve the previous day's XP record
                previous_xp = Xp.objects.filter(user=user, timeStamp__range=(yesterday_start, yesterday_end)).last()

                # Get the total XP for yesterday, defaulting to 0 if no entry exists
                daily_xp = previous_xp.totalXpToday if previous_xp else 0

                # Only reset the streak if yesterday's XP is less than 500
                if daily_xp < 500:
                    streak_record = Streak.objects.filter(user=user).last()
                    streak_record.currentStreak = 0
                    streak_record.save()

                    # Update the streak in the CustomUser model
                    user.streak = 0  # Reset the streak to 0
                    user.save()  # Save the changes to the CustomUser model

        offset += batch_size  # Move to the next batch

    logger.info("Streaks reset task completed successfully.")


@shared_task
def run_company_draws():
    """
    Celery task to run company-specific draws for all companies.
    This is executed monthly.
    """
    # Get all active companies
    companies = Company.objects.all()

    for company in companies:
        # Fetch the active draw for the company
        active_draw = Draw.objects.filter(company=company, is_active=True).first()

        if active_draw:
            # Pick winners for the active draw
            active_draw.pick_winners()
            # Mark the draw as inactive after picking winners
            active_draw.is_active = False
            active_draw.save()

        # Optionally, create a new draw for the next month at 3 PM UTC
        next_draw_date = timezone.now() + timedelta(days=30)  # Approximation for next month
        
        # Set the time to 3 PM UTC
        next_draw_date = next_draw_date.replace(hour=15, minute=0, second=0, microsecond=0)

        Draw.objects.create(
            name=f"Monthly Draw for {company.name}",
            company=company,
            draw_type='company',
            draw_date=next_draw_date,
            number_of_winners=3,  # Example
            is_active=True,  # Activate the new draw
        )



@shared_task
def run_global_draw():
    """
    Task to run the global draw.
    Only one active global draw at a time.
    """

    # Fetch the active global draw
    draw = Draw.objects.filter(is_global=True, is_active=True).first()
    if draw:
        draw.pick_winners()
        draw.is_active = False
        draw.save()

    # Create a new global draw for the next quarter at 3 PM UTC
    next_draw_date = timezone.now() + timedelta(days=90)  # Approximation for a quarter (3 months)
    
    # Set the time to 3 PM UTC
    next_draw_date = next_draw_date.replace(hour=15, minute=0, second=0, microsecond=0)

    Draw.objects.create(
        name="Quarterly Global Draw",
        draw_type='global',
        draw_date=next_draw_date,
        number_of_winners=3,  # Example number of winners
        is_active=True,
    )


@shared_task
def create_global_draw():
    try:
        if not Draw.objects.filter(is_active=True, draw_type='global').exists():
            # Get the current date and time
            now = timezone.now()
            
            # Calculate the next quarter's first day
            month = ((now.month - 1) // 3 + 1) * 3 + 1  # Move to the first month of the next quarter
            if month > 12:  # If month is greater than December, roll over to the next year
                month = 1
                year = now.year + 1
            else:
                year = now.year
            
            # Create the draw date as a naive datetime
            naive_draw_date = datetime(year, month, 1, 15, 0)  # Set the time to 3 PM
            
            # Make the naive datetime timezone-aware
            draw_date = timezone.make_aware(naive_draw_date)

            # Create the Draw instance
            Draw.objects.create(
                name="Global Draw",
                draw_type="global",
                draw_date=draw_date,
                number_of_winners=3,  # Example number
                is_active=True
            )
            print("Global draw created successfully.")
        else:
            print("Global draw already exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


@shared_task
def reset_gems_for_local_timezones():
    """
    This task resets the users' gem amount every Monday at 00:01 AM in their local timezone.
    """
    now_utc = django_timezone.now()

    # Fetch users with timezone info and other necessary fields
    users = CustomUser.objects.values('id', 'email', 'gem', 'timezone')

    for user in users:

        # user['timezone'] is a ZoneInfo object already, so use it directly
        user_timezone = user['timezone']
        
        try:
            # Convert UTC time to user's local time using ZoneInfo
            user_local_time = now_utc.astimezone(user_timezone)  # No need to check if it's a string

            # Check if it's Monday 00:01 AM in the user's local timezone
            if user_local_time.weekday() == 0 and user_local_time.hour == 0 and user_local_time.minute == 1:
                # Reset the gem count to 0
                CustomUser.objects.filter(id=user['id']).update(gem=0)
        except Exception as e:
            print(f"Error processing user {user['email']} with timezone {user['timezone']}: {e}")