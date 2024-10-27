from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Xp, Streak, Company, Draw, League, UserLeague, LeagueInstance, Membership
from django.db.models import Sum
from dateutil.relativedelta import relativedelta
from django.db.models import Count, F

@receiver(post_save, sender=Xp)
def update_streak_on_xp_change(sender, instance, **kwargs):
    print("Signal triggered")
    user = instance.user
    total_xp_today = instance.totalXpToday
    print(f"Total XP today: {total_xp_today}")

    # Check if total XP for today is >= 500
    if total_xp_today < 500:
        print("Total XP is less than 500, not updating streak")
        return

    current_date = timezone.now().date()

    # Check if a streak record exists for today
    streak_record = Streak.objects.filter(user=user, timeStamp__date=current_date).first()

    # If a streak record exists for today, exit
    if streak_record:
        print("Streak record already exists for today, exiting")
        return  # Streak has already been updated today

    # Check for a previous streak record from yesterday
    previous_date = current_date - timezone.timedelta(days=1)
    previous_streak_record = Streak.objects.filter(user=user, timeStamp__date=previous_date).first()

    if previous_streak_record:
        # If a previous record exists, get the current and highest streak values
        current_streak = previous_streak_record.currentStreak
        highest_streak = previous_streak_record.highestStreak
        print("Previous streak record found, using existing values")
    else:
        # If no previous record, initialize current streak to 0 and highest streak to 0
        current_streak = 0
        highest_streak = 0
        print("No previous streak record found, initializing to zero")

    # Create a new streak record for today
    streak_record = Streak.objects.create(
        user=user,
        currentStreak=current_streak + 1,  # Increment the current streak by 1
        highestStreak=max(highest_streak, current_streak + 1),  # Update highest streak if necessary
        timeStamp=timezone.now()  # Set the current timestamp
    )
    
    # Update the streak in the CustomUser model
    user.streak += 1  # Increment the streak by 1
    user.save()  # Save the changes to the CustomUser model

    print("Streak record created and updated")



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
def update_gems(sender, instance, **kwargs):
    user = instance.user
    total_xp_today = instance.totalXpToday

    # Calculate how many gems to award based on the total XP for today
    new_gems_awarded = int(total_xp_today // 250)  # Ensure integer division for whole gems

    # Check if `gems_awarded` needs updating
    if instance.gems_awarded != new_gems_awarded:
        instance.gems_awarded = new_gems_awarded
        instance.save(update_fields=['gems_awarded'])

    # Calculate total gems awarded (sum of gems_awarded from all Xp records)
    total_gems_awarded = user.xp_records.aggregate(total_gems_awarded=Sum('gems_awarded'))['total_gems_awarded'] or 0
    
    # Calculate available gems (total awarded - gems spent)
    # Calculate available gems, ensuring no negative values
    user.gem = max(0, total_gems_awarded - user.gems_spent)
    user.save(update_fields=['gem'])

    print(f"Updated {user.email}'s available gems to {user.gem} based on today's XP.")


@receiver(post_save, sender=Xp)
def add_to_first_league(sender, instance, **kwargs):
    """
    This signal assigns users with total XP >= 65 to the Pathfinder League (level one league).
    If no Pathfinder LeagueInstance has available space, a new instance is created.
    """
    user = instance.user
    total_xp = instance.totalXpAllTime
    print(total_xp)
    
    # Check if user's total XP qualifies them for the Pathfinder league
    if total_xp >= 65:
        pathfinder_league = League.objects.filter(name="Pathfinder League", order=1).first()

        if not pathfinder_league:
            print("Error: Pathfinder league not found.")
            return

        # Check if the user is already in the Pathfinder league
        user_league_entry = UserLeague.objects.filter(user=user, league_instance__league=pathfinder_league).first()
        print(user_league_entry)
        if user_league_entry:
            return  # User is already assigned to the Pathfinder league
        
        # Find or create a new LeagueInstance for Pathfinder League with less than max participants
        pathfinder_instance = (
            LeagueInstance.objects
            .filter(league=pathfinder_league, company=None, is_active=True)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not pathfinder_instance:
            # Create a new Pathfinder LeagueInstance if no open instance exists
            pathfinder_instance = LeagueInstance.objects.create(
                league=pathfinder_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),  # Example: set for a 1-week league duration
                max_participants=30
            )

        # Add user to the Pathfinder LeagueInstance
        UserLeague.objects.create(user=user, league_instance=pathfinder_instance, xp_global=0)
        print(f"User {user} added to {pathfinder_instance.league.name}.")


# Constants for minimum users and XP thresholds
MIN_USERS_FOR_LEAGUE = 5  # Minimum users to create the first league
XP_THRESHOLD = [0, 100, 200, 400, 800, 1600]  # Example XP thresholds for leagues

# Function to adjust company leagues based on membership count
def adjust_company_leagues(company):
    company_member_count = company.members.count()

    # Check if the number of members is above the minimum requirement
    if company_member_count >= MIN_USERS_FOR_LEAGUE:
        # Define the number of leagues based on the number of users
        num_leagues = min(10, (company_member_count // MIN_USERS_FOR_LEAGUE))

        # Create league instances if they don't exist
        existing_leagues = LeagueInstance.objects.filter(company=company).count()

        for order in range(existing_leagues + 1, num_leagues + 1):
            # Assuming you have a League object created with the correct order
            league = League.objects.get(order=order)
            LeagueInstance.objects.create(
                league=league,
                company=company,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),  # Example duration
                max_participants=30,
                is_active=True,
            )

# Signal to create initial league instances when a new company is created
# @receiver(post_save, sender=Company)
# def create_initial_league_instances(sender, instance, created, **kwargs):
#     if created:
#         adjust_company_leagues(instance)

# # Function to assign users to the appropriate leagues
# @receiver(post_save, sender=Membership)
# def assign_user_to_company_league(sender, instance, created, **kwargs):
#     if created:
#         user = instance.user
#         company = instance.company

#         # Check if leagues are set up for this company
#         league_instances = LeagueInstance.objects.filter(company=company).order_by('league__order')

#         if league_instances.exists():
#             # Assign the user to the lowest league instance
#             lowest_league_instance = league_instances.first()
#             UserLeague.objects.create(
#                 user=user,
#                 league_instance=lowest_league_instance,
#                 xp_company=0,
#                 xp_global=0,
#                 is_retained=False
#             )
