from celery import shared_task
from .email_utils import send_invitation_email
from django.utils import timezone
from .models import Streak, CustomUser, Xp, Draw, Company,LeagueInstance, UserLeague, Gem
import logging
from datetime import timedelta, datetime
from django.utils import timezone as django_timezone
from .league_service import promote_user, demote_user, retain_user, promote_company_user, demote_company_user, retain_company_user
from dateutil.relativedelta import relativedelta  # For precise next-month calculation
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Max, F
from .s3_utils import save_file_to_s3
import os

# Configure logging
logging.basicConfig(level=logging.INFO)  # You can adjust the logging level as needed
logger = logging.getLogger(__name__)



@shared_task
def send_invitation_email_task(invite_code, company_name, inviter_name, to_email):
    return send_invitation_email(invite_code, company_name, inviter_name, to_email)


@shared_task
def upload_file_task(file_path, folder_name, file_type, user_id=None, draw_id=None):
    with open(file_path, 'rb') as file:
        s3_url = save_file_to_s3(file_path, folder_name, file_type)

    if user_id:
        user = CustomUser.objects.get(id=user_id)
        user.profile_picture = s3_url
        user.save()
    elif draw_id:
        draw = Draw.objects.get(id=draw_id)
        draw.video = s3_url
        draw.save()

    os.remove(file_path)  # Clean up the temporary file
    

@shared_task
def reset_daily_streaks():
    # Batch size for processing users
    batch_size = 100  # Adjust based on your needs
    offset = 0

    while True:
        # Fetch users who have a timezone set and whose current streak is greater than 0
        users = CustomUser.objects.exclude(timezone=None).filter(streak__gt=0)[offset:offset + batch_size]
        
        if not users:  # Exit if no more users are left
            logger.info("Processed all users successfully.")
            break

        for user in users:
            # Get the current time in the user's timezone
            current_utc_time = timezone.now()
            user_local_time = current_utc_time.astimezone(user.timezone)
            print(f'{user} local time', user_local_time)
            print(f'{user} local hour', user_local_time.hour)

            # Check if the current time is midnight in the user's local time
            if user_local_time.hour == 0 and user_local_time.minute < 60:
                # Define yesterday's start and end times in the user's local timezone
                yesterday_start_local = (user_local_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).replace(tzinfo=None)
                yesterday_end_local = (user_local_time.replace(hour=23, minute=59, second=59, microsecond=999999) - timedelta(days=1)).replace(tzinfo=None)
                day_before_yesterday_start_local = (yesterday_start_local - timedelta(days=1)).replace(tzinfo=None)

                # Retrieve the previous day's XP record
                previous_xp = Xp.objects.filter(user=user, timeStamp__range=(yesterday_start_local, yesterday_end_local)).last()
                if previous_xp:
                    # If there is already a record for yesterday, it means the streak saver was used or XP was sufficient
                    logger.info(f"Xp record for {user.email} already exists for {yesterday_start_local.date()}.")

                # Check if there's already a streak record for yesterday
                existing_streak = Streak.objects.filter(user=user, date=yesterday_start_local.date()).exists()
                if existing_streak:
                    # If there is already a record for yesterday, it means the streak saver was used or XP was sufficient
                    logger.info(f"Streak record for {user.email} already exists for {yesterday_start_local.date()}. Skipping.")
                    continue

                # Retrieve the day before yesterday's streak record
                previous_streak = Streak.objects.filter(user=user, date=day_before_yesterday_start_local.date()).last()
                if previous_streak:
                    # If there is already a streak record for the day before yesterday, it means the streak saver
                    # was used or XP was sufficient
                    logger.info(f"Streak record for {user.email} already exists for day before yesterday {day_before_yesterday_start_local.date()}")

                # Get the total XP for yesterday, defaulting to 0 if no entry exists
                daily_xp = previous_xp.totalXpToday if previous_xp else 0

                # Calculate the highest streak value up to today
                highest_streak = Streak.objects.filter(user=user).aggregate(max_streak=Max('highestStreak'))['max_streak'] or 0

                # Only reset the streak if yesterday's XP is less than 250
                if daily_xp < 250:
                    if user.streak_savers > 0:
                        # Use a streak saver
                        user.streak_savers -= 1
                        # Create the streak record for yesterday
                        current_streak = (previous_streak.currentStreak if previous_streak else 0) + 1
                        
                        
                        Streak.objects.create(
                            user=user,
                            date=yesterday_start_local.date(),
                            timeStamp=yesterday_end_local,
                            currentStreak=current_streak,
                            highestStreak=max(highest_streak + 1, current_streak)
                        )
                        
                        logger.info(f"Used a streak saver for user {user.email}. Remaining streak savers: {user.streak_savers}")
                        user.streak = current_streak
                    else:
                        # Reset the streak to 0
                        user.streak = 0
                        logger.info(f"Reset streak for user {user.email} to 0.")
                    
                    user.save(update_fields=['streak', 'streak_savers'])

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
        # Fetch the active draw for the company whose draw_date has passed
        active_draw = Draw.objects.filter(
            company=company,
            is_active=True,
            draw_date__lte=timezone.now()  # Only include draws where the date has passed
        ).first()

        if active_draw:
            # Pick winners for the active draw
            active_draw.pick_winners()
            # Mark the draw as inactive after picking winners
            active_draw.is_active = False
            active_draw.save()

        # Calculate the start and end of the "next month" window
        current_date = timezone.now()
        next_month_start = (current_date + relativedelta(months=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month_end = (next_month_start + relativedelta(months=1)) - timedelta(seconds=1)

        # Check if there's already an active draw for the next month
        existing_next_month_draw = Draw.objects.filter(
            company=company,
            draw_type='company',
            is_active=True,
            draw_date__range=(next_month_start, next_month_end)
        ).exists()

        if not existing_next_month_draw:
            # Create a new draw for the next month at 3 PM UTC
            next_draw_date = next_month_start.replace(hour=15)

            Draw.objects.create(
                draw_name=f"Monthly Draw for {company.name}",
                company=company,
                draw_type='company',
                draw_date=next_draw_date,
                number_of_winners=3,  # Example number of winners
                is_active=True,  # Activate the new draw
            )


@shared_task
def run_global_draw():
    """
    Task to run the global draw.
    Only one active global draw at a time.
    """
    # Fetch the active global draw whose draw_date has passed
    draw = Draw.objects.filter(
        draw_type='global', 
        is_active=True, 
        draw_date__lte=timezone.now()  # Only get draws where the draw_date is less than or equal to the current time
    ).first()
    
    print(draw)

    if draw:
        # Execute the draw logic if the draw date has passed
        draw.pick_winners()
        draw.is_active = False
        draw.save()

        # Create a new global draw for the next quarter at 3 PM UTC
        next_draw_date = timezone.now() + timedelta(days=90)  # Approximation for a quarter (3 months)
        # Set the time to 3 PM UTC
        next_draw_date = next_draw_date.replace(hour=15, minute=0, second=0, microsecond=0)

        # Create a new global draw
        Draw.objects.create(
            draw_name="Quarterly Global Draw",
            draw_type='global',
            draw_date=next_draw_date,
            number_of_winners=3,  # Number of winners
            is_active=True,
        )
    else:
        # Log or handle case when no active global draw has passed
        print("No active global draw with a passed date found.")


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
                draw_name="Global Draw",
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
    This task resets the users' gem amount and gems spent every day at midnight in their local timezone.
    """
    now_utc = django_timezone.now()
    
    batch_size = 100  # Adjust based on your needs
    offset = 0

    while True:
        # Fetch users with timezones in batches
        users = CustomUser.objects.exclude(timezone=None).values('id', 'email', 'gems_spent', 'timezone')[offset:offset + batch_size]

        if not users:
            print("Processed all users successfully.")
            break

        for user in users:
            user_timezone = user['timezone']

            try:
                # Convert UTC time to user's local time
                user_local_time = now_utc.astimezone(user_timezone)

                # Check if it's midnight (0 hour) in the user's local timezone
                if user_local_time.hour == 0:
                    # Calculate the date for the previous day 
                    previous_day = user_local_time.date() - timedelta(days=1)

                    # Reset the user's total gems and gems spent
                    CustomUser.objects.filter(id=user['id']).update(gems_spent=0)

                    # Update gem records for the previous day to keep copies and reset daily values 
                    Gem.objects.filter(user_id=user['id'], date=previous_day).update( 
                        xp_gem=0, 
                        manual_gem=0 
                    )

                    print(f"Reset gems and gems spent for user {user['email']}")

            except Exception as e:
                print(f"Error processing user {user['email']} with timezone {user['timezone']}: {e}")

        offset += batch_size

    print("Gem reset task completed successfully.")


@shared_task(acks_late=True)
def process_league_promotions():
    # Get current time
    now = timezone.now()
    
    # Query leagues where the end date has passed but still active
    expired_leagues = LeagueInstance.objects.filter(league_end__lte=now, is_active=True, company__isnull=True)
    
    for league in expired_leagues:
        # Order users by global XP in descending order for promotions and demotions
        users_in_league = UserLeague.objects.filter(league_instance=league).order_by('-xp_global', 'id')
        total_users = users_in_league.count()

        promotion_threshold = int(total_users * 0.30)  # Promote top 30%
        demotion_threshold = int(total_users * 0.80)

        for rank, user_league in enumerate(users_in_league, start=1):
            user = user_league.user
            # Apply logic based on user count and rank position
            if total_users <= 3:
                # Handle cases with very few users separately
                if user_league.xp_global == 0:
                    gems_obtained = 0
                    demote_user(user,gems_obtained, league)
                else:
                    gems_obtained = 10
                    retain_user(user,gems_obtained, league)
            else:
                # Standard promotion/retention/demotion logic
                if rank <= promotion_threshold:
                    gems_obtained = 20 - (rank - 1) * 2  # Reward for promotion
                    promote_user(user,gems_obtained, league)
                elif rank <= demotion_threshold:
                    gems_obtained = 10  # Base reward for retained users
                    retain_user(user,gems_obtained, league)
                else:
                    gems_obtained = 0  # No reward for demoted users
                    demote_user(user,gems_obtained, league)

            # Reset the user global XP for the new league week
            user_league.xp_global = 0
            user_league.save()

            # Broadcast gem update 
            new_gem_count = user.get_gem_count() 
            channel_layer = get_channel_layer() 
            async_to_sync(channel_layer.group_send)( 
                f'gem_{user.id}', 
                { 
                    'type': 'send_gem_update', 
                    'gem_count': new_gem_count, 
                } 
            )
        
        # Broadcast league update 
        rankings = UserLeague.objects.filter(league_instance=league).select_related('user').order_by('-xp_global', 'id') 
        rankings_data = [] 
        for idx, ul in enumerate(rankings, start=1): 
            rankings_data.append({ 
                "user_id": ul.user.id, 
                "username": ul.user.username, 
                "profile_picture": ul.user.profile_picture.url if ul.user.profile_picture else None, 
                "xp": ul.xp_global, 
                "streaks": ul.user.streak, 
                "rank": idx, 
                "advancement": "Promoted" if idx <= promotion_threshold else "Retained" if idx <= demotion_threshold else "Demoted", 
            }) 
        data = { 
            "league_id": league.id,
            "league_name": league.league.name, 
            "league_level": 11 - league.league.order, 
            "league_start": league.league_start, 
            "league_end": league.league_end, 
            "rankings": rankings_data, 
        } 
        async_to_sync(channel_layer.group_send)( 
            f'global_league_{league.id}', 
            { 
                'type': 'send_league_update', 
                'data': data, 
            }
        )

        # Mark this league instance as inactive
        league.is_active = False
        league.save()


@shared_task
def process_company_league_promotions():
    """
    Handles promotions and demotions of users in company leagues at the end of a league period.
    """
    now = timezone.now()
    expired_leagues = LeagueInstance.objects.filter(league_end__lte=now, is_active=True, company__isnull=False)
    print('Expired company league', expired_leagues)

    for league in expired_leagues:
        # Get users ordered by company XP for promotions and demotions
        users_in_league = UserLeague.objects.filter(league_instance=league).order_by('-xp_company', 'id')

        total_users = users_in_league.count()
        
        promotion_threshold = int(total_users * 0.30)
        demotion_threshold = int(total_users * 0.80)

        for rank, user_league in enumerate(users_in_league, start=1):
            user = user_league.user

            if total_users <= 3:
                # Handle cases with very few users separately
                if user_league.xp_global == 0:
                    gems_obtained = 0
                    demote_company_user(user,gems_obtained, league)
                else:
                    gems_obtained = 10
                    retain_company_user(user,gems_obtained, league)
            else:
                # Standard promotion/retention/demotion logic
                if rank <= promotion_threshold:
                    gems_obtained = 20 - (rank - 1) * 2  # Reward for promotion
                    promote_company_user(user,gems_obtained, league)
                elif rank <= demotion_threshold:
                    gems_obtained = 10  # Base reward for retained users
                    retain_company_user(user,gems_obtained, league)
                else:
                    gems_obtained = 0  # No reward for demoted users
                    demote_company_user(user,gems_obtained, league)


            # Reset XP for the new league week
            user_league.xp_company = 0
            user_league.save()

           # Broadcast gem update 
            new_gem_count = user.get_gem_count() 
            channel_layer = get_channel_layer() 
            async_to_sync(channel_layer.group_send)( 
                f'gem_{user.id}', 
                { 
                    'type': 'send_gem_update', 
                    'gem_count': new_gem_count, 
                } 
            )
        
        # Broadcast league update 
        rankings = UserLeague.objects.filter(league_instance=league).select_related('user').order_by('-xp_company', 'id') 
        rankings_data = [] 
        for idx, ul in enumerate(rankings, start=1): 
            rankings_data.append({ 
                "user_id": ul.user.id, 
                "username": ul.user.username, 
                "profile_picture": ul.user.profile_picture.url if ul.user.profile_picture else None, 
                "xp": ul.xp_global, 
                "streaks": ul.user.streak, 
                "rank": idx, 
                "advancement": "Promoted" if idx <= promotion_threshold else "Retained" if idx <= demotion_threshold else "Demoted", 
            }) 
        data = { 
            "league_id": league.id,
            "league_name": league.league.name, 
            "league_level": 11 - league.league.order, 
            "league_start": league.league_start, 
            "league_end": league.league_end, 
            "rankings": rankings_data, 
        } 
        async_to_sync(channel_layer.group_send)( 
            f'company_league_{league.id}', 
            { 
                'type': 'send_league_update', 
                'data': data, 
            }
        )

        # Mark the league instance as inactive
        league.is_active = False
        league.save()