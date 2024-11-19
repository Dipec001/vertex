from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Xp, Streak, Company, Draw, League, UserLeague, LeagueInstance, Feed, Gem
from django.db.models import Sum
from dateutil.relativedelta import relativedelta
from django.db.models import Count, F
from datetime import timedelta, datetime
from django.db import transaction
import pytz
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection
from django.core.signals import request_finished
from django.dispatch import receiver

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
            print(f"Streak record updated for date: {xp_date}")
        else:
            print(f"Streak record created for date: {xp_date}")

        # Dynamic milestone check
        if is_milestone_streak(current_streak):
            Feed.objects.create(
                user=user,
                feed_type=Feed.STREAK,
                content=f"{user.username} has reached a {current_streak}-day streak!",
            )
            print(f"Feed created for {current_streak}-day streak milestone.")

        # Ensure proper conversion to user's local timezone
        user_timezone = pytz.timezone(user.timezone.key)
        local_now = datetime.now(user_timezone)
        # print('local time',local_now)

        current_date = xp_date + timedelta(days=1)  # Start checking from the next day

        while current_date <= local_now.date():
            # Check if a streak record exists for this date
            streak_record = Streak.objects.filter(user=user, date=current_date).first()
            print(streak_record,f'for day {current_date}')


            if streak_record:
                # Update existing record for current_date
                # Increment the streak for each existing record
                current_streak += 1
                streak_record.currentStreak = current_streak
                streak_record.highestStreak = max(streak_record.highestStreak, current_streak)
                streak_record.save()
                print(f"Streak record updated for date: {current_date}")
            else:
                # Break the streak if no XP was gained for the day
                print(f"No XP gained on {current_date}. Streak breaks.")
                break

            current_date += timedelta(days=1)

        # Correct the current streak before updating the CustomUser model
        user.streak = current_streak
        user.save()
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


@receiver(post_save, sender=Xp)
def update_gem_for_xp(sender, instance, **kwargs):
    user = instance.user
    xp_today = instance.totalXpToday
    # Calculate gems awarded based on XP (1 gem per 250 XP)
    xp_gem = int(xp_today // 250)  # Calculate XP-based gems

    # Try to create or update the Gem record for the user
    gem, created = Gem.objects.get_or_create(user=user, date=instance.date)
    gem.xp_gem = xp_gem
    gem.save()


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
                league_end=timezone.now() + timezone.timedelta(hours=1),  # Example: set for a 1-week league duration
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
    print('Add to Company league triggered')
    user = instance.user
    total_xp = instance.totalXpAllTime
    company = user.company
    
    # Check if user's total XP qualifies them for the Pathfinder league
    if total_xp >= 80:
        pathfinder_league = League.objects.filter(name="Pathfinder league", order=1).first()

        if not pathfinder_league:
            print("Error: Pathfinder league not found.")
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
                league_end=timezone.now() + timezone.timedelta(hours=1),
                max_participants=10
            )

        # Add the user to the Pathfinder league instance
        UserLeague.objects.create(user=user, league_instance=pathfinder_instance, xp_company=0)
        print(f"User {user} added to the {pathfinder_instance.league.name} instance for {company.name}.")



# @receiver(post_save, sender=Xp)
# def broadcast_global_league_ranking_update(sender, instance, **kwargs):
#     user = instance.user

#     # Get the user's active global league instance
#     user_league = (
#         UserLeague.objects
#         .filter(user=user, league_instance__is_active=True, league_instance__company__isnull=True)
#         .select_related('league_instance', 'user')
#         .first()
#     )

#     if not user_league:
#         return  # No active global league found, exit early

#     league_instance = user_league.league_instance
#     print(league_instance.id)

#     # Fetch all users in the league and calculate rankings
#     rankings = UserLeague.objects.filter(
#         league_instance=league_instance
#     ).select_related('user').order_by('-xp_global', 'id')

#     total_users = rankings.count()
#     promotion_threshold = int(total_users * 0.30)  # Top 30%
#     demotion_threshold = int(total_users * 0.80)  # Bottom 20%

#     rankings_data = []
#     for index, ul in enumerate(rankings, start=1):
#         # Determine advancement status
#         if total_users <= 3:
#             if ul.xp_global == 0:
#                 advancement = "Demoted"
#                 gems_obtained = 0
#             else:
#                 advancement = "Retained"
#                 gems_obtained = 10
#         else:
#             if index <= promotion_threshold:
#                 gems_obtained = 20 - (index - 1) * 2  # Reward for promotion
#                 advancement = "Promoted"
#             elif index <= demotion_threshold:
#                 gems_obtained = 10  # Retained users get a base reward
#                 advancement = "Retained"
#             else:
#                 gems_obtained = 0  # Demoted users receive no gems
#                 advancement = "Demoted"

#         # Prefix for S3 bucket URL
#         s3_bucket_url = "https://video-play-api-bucket.s3.amazonaws.com/"

#         # User data for each ranking
#         rankings_data.append({
#             "user_id": ul.user.id,
#             "username": ul.user.username,
#             "profile_picture": f"{s3_bucket_url}{ul.user.profile_picture}" if ul.user.profile_picture else None,
#             "xp": ul.xp_global,
#             "streaks": ul.user.streak,
#             "gems_obtained": gems_obtained,
#             "rank": index,
#             "advancement": advancement,
#         })

#     # Find the current user's rank
#     user_rank = next((index for index, r in enumerate(rankings_data, start=1) if r["user_id"] == user.id), None)

#     # Prepare data to send
#     data = {
#         "league_name": league_instance.league.name,
#         "league_level": 11 - league_instance.league.order,
#         "league_start": league_instance.league_start.isoformat(),
#         "league_end": league_instance.league_end.isoformat(),
#         "user_rank": user_rank,
#         "rankings": rankings_data,
#     }

#     print(data,' data from enw singnal')
#     # Send the data to the WebSocket group
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         f'league_{league_instance.id}',
#         {
#             'type': 'send_league_update',
#             'data': data,
#         }
#     )
