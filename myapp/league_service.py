from django.db.models import Count, F
from .models import UserLeague, LeagueInstance, League
from django.utils import timezone
from django.db import IntegrityError

# def promote_user(user):
#     next_league = League.objects.filter(order__gt=user.league.order).order_by('order').first()
#     if next_league:
#         # Deactivate the current league membership
#         UserLeague.objects.filter(user=user, is_active=True).update(is_active=False)

#         # Find an available LeagueInstance for the next league
#         next_league_instance = (
#             LeagueInstance.objects
#             .filter(league=next_league, is_company=False)
#             .annotate(participant_count=Count('userleague'))
#             .filter(participant_count__lt=F('max_participants'))
#             .first()
#         )

#         if not next_league_instance:
#             # Create a new instance if none are available
#             next_league_instance = LeagueInstance.objects.create(
#                 league=next_league,
#                 league_start=timezone.now(),
#                 league_end=timezone.now() + timezone.timedelta(days=7),  # Example duration
#                 max_participants=30
#             )

#         # Create a new UserLeague entry for the user
#         UserLeague.objects.create(user=user, league_instance=next_league_instance, xp=0)
#         return f"{user.username} has been promoted to {next_league.name}"
#     return f"{user.username} is already at the highest league level."


def promote_user(user):
    current_user_league = UserLeague.objects.filter(user=user, league_instance__is_active=True).first()

    if not current_user_league:
        return f"{user.username} is not currently in an active league instance."

    current_league = current_user_league.league_instance.league
    next_league = League.objects.filter(order__gt=current_league.order).order_by('order').first()

    if next_league:
        # Find an available LeagueInstance for the next league
        next_league_instance = (
            LeagueInstance.objects
            .filter(league=next_league, is_active=True, company__isnull=True)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )
        
        if not next_league_instance:
            # Create a new instance if none are available
            next_league_instance = LeagueInstance.objects.create(
                league=next_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),
                max_participants=30
            )

        # Check if a UserLeague entry already exists for this user and league instance
        if not UserLeague.objects.filter(user=user, league_instance=next_league_instance).exists():
            try:
                # Create a new UserLeague entry for the user
                UserLeague.objects.create(user=user, league_instance=next_league_instance, xp_global=0)
                return f"{user.username} has been promoted to {next_league.name}"
            except IntegrityError:
                # Handle a rare case where a duplicate might occur due to race conditions
                return f"{user.username} is already in the target league instance."

    else:
        # reward_user_for_top_league(user)  # Hypothetical function
        return f"{user.username} is already at the highest league level and has received a reward for top performance."




# def demote_user(user):
#     previous_league = League.objects.filter(order__lt=user.league.order).order_by('-order').first()
#     if previous_league:
#         # Deactivate the current league membership
#         UserLeague.objects.filter(user=user, is_active=True).update(is_active=False)

#         # Find an available LeagueInstance for the previous league
#         previous_league_instance = (
#             LeagueInstance.objects
#             .filter(league=previous_league, is_company=False)
#             .annotate(participant_count=Count('userleague'))
#             .filter(participant_count__lt=F('max_participants'))
#             .first()
#         )

#         if not previous_league_instance:
#             # Create a new instance if none are available
#             previous_league_instance = LeagueInstance.objects.create(
#                 league=previous_league,
#                 league_start=timezone.now(),
#                 league_end=timezone.now() + timezone.timedelta(days=7),  # Example duration
#                 max_participants=30
#             )

#         # Create a new UserLeague entry for the user
#         UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp=0)
#         return f"{user.username} has been demoted to {previous_league.name}"
#     return f"{user.username} is already at the lowest league level."


def demote_user(user):
    current_user_league = UserLeague.objects.filter(user=user, league_instance__is_active=True).first()
    
    if not current_user_league:
        return f"{user.username} is not currently in an active league instance."

    current_league = current_user_league.league_instance.league
    previous_league = League.objects.filter(order__lt=current_league.order).order_by('-order').first()

    if previous_league:
        # Deactivate the current league membership by deleting or updating as needed
        current_user_league.delete()

        # Find an available LeagueInstance for the previous league
        previous_league_instance = (
            LeagueInstance.objects
            .filter(league=previous_league, is_active=True, company__isnull=True)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not previous_league_instance:
            # Create a new instance if none are available
            previous_league_instance = LeagueInstance.objects.create(
                league=previous_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),
                max_participants=5
            )

        UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp_global=0)
        return f"{user.username} has been demoted to {previous_league.name}"
    else:
        # User is already at the lowest league, reassign to a new instance in the lowest league
        lowest_league = League.objects.order_by('order').first()

        if lowest_league:
            # Create or reuse an instance of the lowest league
            lowest_league_instance = (
                LeagueInstance.objects
                .filter(league=lowest_league, is_active=True, company__isnull=True)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )
            
            if not lowest_league_instance:
                # Create a new instance if none are available
                lowest_league_instance = LeagueInstance.objects.create(
                    league=lowest_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(days=7),
                    max_participants=5
                )

            UserLeague.objects.create(user=user, league_instance=lowest_league_instance, xp_global=0)
            return f"{user.username} has been reassigned to a new instance in the lowest league: {lowest_league.name}."
