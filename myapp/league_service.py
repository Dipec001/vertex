from django.db import transaction, IntegrityError
from django.db.models import Count, F
from .models import UserLeague, LeagueInstance, League
from django.utils import timezone


def promote_user(user):
    with transaction.atomic():
        # Find the user's current active league
        current_user_league = UserLeague.objects.select_related('league_instance__league').filter(
            user=user, league_instance__is_active=True).first()

        if not current_user_league:
            return f"{user.username} is not currently in an active league instance."

        current_league = current_user_league.league_instance.league
        next_league = League.objects.filter(order__gt=current_league.order).order_by('order').first()

        if next_league:
            # Find or create an available LeagueInstance for the next league
            next_league_instance = (
                LeagueInstance.objects
                .filter(league=next_league, is_active=True, company__isnull=True)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )
            
            if not next_league_instance:
                next_league_instance = LeagueInstance.objects.create(
                    league=next_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(days=7),
                    max_participants=30
                )

            # Attempt to create a new UserLeague entry for the user
            try:
                UserLeague.objects.create(user=user, league_instance=next_league_instance, xp_global=0)
                current_user_league.delete()
                return f"{user.username} has been promoted to {next_league.name}"
            except IntegrityError:
                return f"{user.username} is already in the target league instance."

        else:
            # Handle users in the highest league by reassigning them to another instance of that league
            highest_league_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company__isnull=True)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not highest_league_instance:
                highest_league_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(days=7),
                    max_participants=30
                )

            try:
                UserLeague.objects.create(user=user, league_instance=highest_league_instance, xp_global=0)
                current_user_league.delete()
                return f"{user.username} has been reassigned within the highest league: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."


def demote_user(user):
    with transaction.atomic():
        current_user_league = UserLeague.objects.select_related('league_instance__league').filter(
            user=user, league_instance__is_active=True).first()

        if not current_user_league:
            return f"{user.username} is not currently in an active league instance."

        current_league = current_user_league.league_instance.league
        previous_league = League.objects.filter(order__lt=current_league.order).order_by('-order').first()

        if previous_league:
            # Deactivate the current league membership by deleting the current UserLeague entry
            current_user_league.delete()

            # Find or create an available LeagueInstance for the previous league
            previous_league_instance = (
                LeagueInstance.objects
                .filter(league=previous_league, is_active=True, company__isnull=True)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not previous_league_instance:
                previous_league_instance = LeagueInstance.objects.create(
                    league=previous_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(days=7),
                    max_participants=5
                )

            UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp_global=0)
            return f"{user.username} has been demoted to {previous_league.name}"

        else:
            # Handle users in the lowest league by reassigning them to another instance of that league
            lowest_league_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company__isnull=True)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not lowest_league_instance:
                lowest_league_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(days=7),
                    max_participants=5
                )

            try:
                UserLeague.objects.create(user=user, league_instance=lowest_league_instance, xp_global=0)
                current_user_league.delete()
                return f"{user.username} has been reassigned within the lowest league: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."
