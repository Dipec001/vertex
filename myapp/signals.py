from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Xp, Streak, Company, Draw, League, UserLeague, LeagueInstance, Feed, Gem, Notif
from dateutil.relativedelta import relativedelta
from django.db.models import Count, F
from datetime import timedelta, datetime
from django.db import transaction
import pytz
from django.db import connection
from django.core.signals import request_finished
from django.dispatch import receiver
import re
import redis
import os
from dotenv import load_dotenv

load_dotenv()


r = redis.Redis(host=os.getenv('REDIS_HOST'), port=12150, db=0)

@receiver(request_finished)
def close_redis_connection(sender, **kwargs):
    r.close()


@receiver(request_finished)
def close_db_connection(sender, **kwargs):
    connection.close()



def is_milestone_streak(streak):
    # Define milestones dynamically
    if streak < 10:
        return False
    elif streak % 10 == 0 and streak < 100:
        return True
    elif streak % 100 == 0 and streak < 1000:
        return True
    elif streak % 1000 == 0 and streak < 1000000:
        return True
    elif streak % 1000000 == 0:
        return True
    return False


@receiver(post_save, sender=Xp)
def update_streak_on_xp_change(sender, instance, **kwargs):
    # print("Signal triggered")
    user = instance.user
    total_xp_today = instance.totalXpToday
    # print(f"Total XP today: {total_xp_today}")

    # Check if total XP for today is >= 250
    if total_xp_today < 250:
        # print("Total XP is less than 500, not updating streak")
        return

    xp_date = instance.date  # Use the date from Xp instance

    with transaction.atomic():
        # Get the most recent streak record before the given xp_date
        recent_streak = Streak.objects.filter(user=user, date__lt=xp_date).order_by('-date').first()
        # print('Recent streak date:', recent_streak.date if recent_streak else None)
    
        # Determine the starting streak value and highest streak value
        if recent_streak:
            if (xp_date - recent_streak.date).days == 1:
                current_streak = recent_streak.currentStreak + 1
                highest_streak = max(recent_streak.highestStreak, current_streak)
            else:
                current_streak = 1
                highest_streak = recent_streak.highestStreak
        else:
            current_streak = 1
            highest_streak = 1

        current_date = xp_date

        # Create or update the streak record for the given xp_date
        streak_record, created = Streak.objects.get_or_create(
            user=user,
            date=xp_date,
            defaults={
                'currentStreak': current_streak,
                'highestStreak': highest_streak,
                'timeStamp': instance.timeStamp,
            }
        )

        if not created:
            streak_record.currentStreak = current_streak
            streak_record.highestStreak = highest_streak
            streak_record.timeStamp = instance.timeStamp
            streak_record.save()
            # print(f"Streak record updated for date: {xp_date}")
        else:
            print(f"Streak record created for date: {xp_date}")

        # Ensure proper conversion to user's local timezone
        user_timezone = pytz.timezone(user.timezone.key)
        local_now = datetime.now(user_timezone)

        current_date = xp_date + timedelta(days=1)  # Start checking from the next day

        while current_date <= local_now.date():
            # Check if a streak record exists for this date
            streak_record = Streak.objects.filter(user=user, date=current_date).first()


            if streak_record:
                # Update existing record for current_date
                # Increment the streak for each existing record
                current_streak += 1
                streak_record.currentStreak = current_streak
                streak_record.highestStreak = max(streak_record.highestStreak, current_streak)
                streak_record.save()
            else:
                # Break the streak if no XP was gained for the day
                break

            current_date += timedelta(days=1)

        # Correct the current streak before updating the CustomUser model
        user.streak = current_streak
        user.save()

        # Dynamic milestone check
        if is_milestone_streak(current_streak):
            # Check the most recent milestone feed for this user
            last_milestone_feed = Feed.objects.filter(
                user=user,
                feed_type=Feed.STREAK
            ).order_by('-created_at').first()

            # Extract the last recorded milestone streak from the feed content
            last_milestone = 0
            if last_milestone_feed:
                # print('last milestone')
                try:
                    # Use regex to extract the milestone number
                    match = re.search(r'has reached a (\d+)-day streak', last_milestone_feed.content)
                    if match:
                        last_milestone = int(match.group(1))  # Extract the number from the match
                except ValueError:
                    last_milestone = 0

            # Only create a feed if the current streak exceeds the last recorded milestone
            if current_streak > last_milestone:
                Feed.objects.create(
                    user=user,
                    feed_type=Feed.STREAK,
                    content=f"{user.username} has reached a {current_streak}-day streak!",
                )
                print(f"Feed created for {current_streak}-day streak milestone.")

        print(f"Updated user streak to: {user.streak}")


@receiver(post_save, sender=Company)
def create_company_draw(sender, instance, created, **kwargs):
    if created:
        # Get today's date
        today = timezone.now()

        # Create draws for the next 3 months
        for i in range(1, 4):  # Loop through the next 3 months
            # Add `i` months to today's date and time should be 3pm utc
            first_of_next_month = (today + relativedelta(months=i)).replace(day=1, hour=15, minute=0, second=0, microsecond=0)

            # Create the draw for the company
            Draw.objects.create(
                draw_name=f"{instance.name} Company Draw - Month {i}",
                draw_type='company',
                draw_date=first_of_next_month,
                number_of_winners=3,  # Example number of winners
                is_active=True,
                company=instance
            )


# @receiver(post_save, sender=Xp)
# def update_gem_for_xp(sender, instance, **kwargs):
#     user = instance.user
#     xp_today = instance.totalXpToday
#     # Calculate gems awarded based on XP (1 gem per 250 XP)
#     xp_gem = int(xp_today // 250)  # Calculate new XP-based gems

#     # Retrieve the user's timezone
#     user_timezone = user.timezone
#     now_utc = timezone.now()
#     user_local_time = now_utc.astimezone(user_timezone)

#     # Fetch today's gem record for the user
#     gem, created = Gem.objects.get_or_create(user=user, date=user_local_time.date())

#     # Calculate the total XP-based gems for today 
#     total_xp_gem_today = xp_gem 
    
#     # Ensure the total does not exceed 5 
#     if total_xp_gem_today > 5: 
#         total_xp_gem_today = 5

#     # Update the gem record
#     gem.xp_gem = total_xp_gem_today
#     gem.copy_xp_gem = total_xp_gem_today
#     gem.save()



@receiver(post_save, sender=Xp)
def update_gem_for_xp(sender, instance, **kwargs):
    user = instance.user
    xp_today = instance.totalXpToday

    # Retrieve the user's timezone
    user_timezone = user.timezone
    now_utc = timezone.now()
    user_local_time = now_utc.astimezone(user_timezone)

    # Calculate the Monday of the current week
    today = user_local_time.date()
    current_week_monday = today - timedelta(days=today.weekday())

    # Check if the XP was gained within the current week
    xp_date = instance.date  # Assuming `date` field exists in Xp model
    xp_timestamp = instance.timeStamp

    # Convert the local xp_date to UTC before querying the database
    xp_utc_time = xp_timestamp.astimezone(pytz.utc)

    if xp_date < current_week_monday:

        return  # Do not award gems if the XP was gained before the current week

    # Calculate gems awarded based on XP (1 gem per 250 XP)
    xp_gem = int(xp_today // 250)

    # Fetch today's gem record for the user
    gem, created = Gem.objects.get_or_create(user=user, date=xp_date)

    # Calculate the total XP-based gems for today
    total_xp_gem_today = xp_gem

    # Ensure the total does not exceed 5
    if total_xp_gem_today > 5:
        # print('gem is greated than 5')
        total_xp_gem_today = 5

    # Update the gem record
    gem.xp_gem = total_xp_gem_today
    gem.copy_xp_gem = total_xp_gem_today
    gem.save()

    # Check if there's already a "received_gem" notification for the user on this day
    existing_notification = Notif.objects.filter(
        user=user,
        notif_type="received_gem",
        created_at__date=xp_utc_time
    ).first()

    if existing_notification:
        # Update the existing "received_gem" notification content
        existing_notification.content = f"You earned {xp_today} XP and therefore, claimed {total_xp_gem_today} gems."
        existing_notification.created_at = timezone.now()  # Update the timestamp to the current time
        existing_notification.save()
    else:
        if total_xp_gem_today > 0:
            # Create a new "received_gem" notification if one doesn't exist for the day
            Notif.objects.create(
                user=user,
                notif_type="received_gem",
                content=f"You earned {xp_today} XP and therefore, claimed {total_xp_gem_today} gems.",
            )



@receiver(post_save, sender=Xp)
def add_to_first_league(sender, instance, **kwargs):
    """
    This signal assigns users with total XP >= 65 to the Pathfinder League (level one league).
    If no Pathfinder LeagueInstance has available space, a new instance is created.
    """
    # print('Add to league triggered')
    user = instance.user
    total_xp = instance.totalXpAllTime
    # print(f"Total xp for the user is {total_xp}")
    
    # Check if user's total XP qualifies them for the Pathfinder league
    if total_xp >= 65:
        pathfinder_league = League.objects.filter(name="Pathfinder league", order=1).first()

        if not pathfinder_league:
            print("Error: Pathfinder league not found.")
            return

        # Check if the user is already in the Pathfinder league
        user_league_entry = UserLeague.objects.filter(user=user, league_instance__league=pathfinder_league).first()
        if user_league_entry:
            return  # User is already assigned to the Pathfinder league
        
        # Find or create a new LeagueInstance for Pathfinder League with less than max participants
        pathfinder_instance = (
            LeagueInstance.objects
            .filter(league=pathfinder_league, company=None, is_active=True, league_end__gt=timezone.now())
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not pathfinder_instance:
            # Create a new Pathfinder LeagueInstance if no open instance exists
            pathfinder_instance = LeagueInstance.objects.create(
                league=pathfinder_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(minutes=10),  # Example: set for a 1-week league duration
                max_participants=10
            )

        # Add user to the Pathfinder LeagueInstance
        UserLeague.objects.create(user=user, league_instance=pathfinder_instance, xp_global=0)
        # print(f"User {user} added to {pathfinder_instance.league.name}.")


# Constants for minimum users and XP thresholds
XP_THRESHOLD = {
    1: 0, 
    2: 100, 
    3: 200, 
    4: 400, 
    5: 800, 
    6: 1600,
    7: 2000,
    8: 4000,
    9: 8000,
    10: 16000
    }  # Example XP thresholds for leagues


@receiver(post_save, sender=Xp)
def add_to_first_company_league(sender, instance, **kwargs):
    """
    Adds a user to the first available Pathfinder league instance for their company upon joining.
    If no instance has room, a new Pathfinder instance is created.
    """
    # print('Add to Company league triggered')
    user = instance.user
    total_xp = instance.totalXpAllTime
    company = user.company
    
    # Check if user's total XP qualifies them for the Pathfinder league
    if total_xp >= 80:
        pathfinder_league = League.objects.filter(name="Pathfinder league", order=1).first()

        if not pathfinder_league:
            # print("Error: Pathfinder league not found.")
            return

        # Check if the user is already assigned to a Pathfinder league for this company
        user_league_entry = UserLeague.objects.filter(
            user=user,
            league_instance__league=pathfinder_league,
            league_instance__company=company
        ).first()
        # print('in company league, user league entry', user_league_entry)

        if user_league_entry:
            return  # User is already in the Pathfinder league for this company

        # Find an active Pathfinder instance with room or create a new one
        pathfinder_instance = (
            LeagueInstance.objects
            .filter(league=pathfinder_league, company=company, is_active=True, league_end__gt=timezone.now())
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not pathfinder_instance:
            # Create a new Pathfinder instance if all are full or none exist
            pathfinder_instance = LeagueInstance.objects.create(
                league=pathfinder_league,
                company=company,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(minutes=15),
                max_participants=10
            )

        # Add the user to the Pathfinder league instance
        UserLeague.objects.create(user=user, league_instance=pathfinder_instance, xp_company=0)
        print(f"User {user} added to the {pathfinder_instance.league.name} instance for {company.name}.")