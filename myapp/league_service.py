from django.db.models import Count, F
from .models import UserLeague, LeagueInstance, League
from django.utils import timezone

def promote_user(user):
    next_league = League.objects.filter(order__gt=user.league.order).order_by('order').first()
    if next_league:
        # Deactivate the current league membership
        UserLeague.objects.filter(user=user, is_active=True).update(is_active=False)

        # Find an available LeagueInstance for the next league
        next_league_instance = (
            LeagueInstance.objects
            .filter(league=next_league, is_company=False)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not next_league_instance:
            # Create a new instance if none are available
            next_league_instance = LeagueInstance.objects.create(
                league=next_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),  # Example duration
                max_participants=30
            )

        # Create a new UserLeague entry for the user
        UserLeague.objects.create(user=user, league_instance=next_league_instance, xp=0)
        return f"{user.username} has been promoted to {next_league.name}"
    return f"{user.username} is already at the highest league level."


def demote_user(user):
    previous_league = League.objects.filter(order__lt=user.league.order).order_by('-order').first()
    if previous_league:
        # Deactivate the current league membership
        UserLeague.objects.filter(user=user, is_active=True).update(is_active=False)

        # Find an available LeagueInstance for the previous league
        previous_league_instance = (
            LeagueInstance.objects
            .filter(league=previous_league, is_company=False)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if not previous_league_instance:
            # Create a new instance if none are available
            previous_league_instance = LeagueInstance.objects.create(
                league=previous_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(days=7),  # Example duration
                max_participants=30
            )

        # Create a new UserLeague entry for the user
        UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp=0)
        return f"{user.username} has been demoted to {previous_league.name}"
    return f"{user.username} is already at the lowest league level."
