from django.db import transaction, IntegrityError
from django.db.models import Count, F
from .models import UserLeague, LeagueInstance, League
from django.utils import timezone
from .utils import add_manual_gem



def promote_user(user, gems_obtained, current_league_instance):
    with transaction.atomic():
        # Find the user's current active league
        current_league = current_league_instance.league

        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())

        # current_league = current_user_league.league_instance.league
        next_league = League.objects.filter(order__gt=current_league.order).order_by('order').first()
        print(f"In the promotion view, promoting user {user.username} from current league {current_league}")


        if next_league:
            print(f'Next league level exists {next_league.name}')
            # Find or create an available LeagueInstance for the next league
            next_league_instance = (
                LeagueInstance.objects
                .filter(league=next_league, is_active=True, company__isnull=True, league_end__gt=timezone.now())
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )
            
            if not next_league_instance:
                print(f'No available league instance for next league {next_league.name}, creating...')
                next_league_instance = LeagueInstance.objects.create(
                    league=next_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    max_participants=10
                )

            # Attempt to create a new UserLeague entry for the user
            try:
                UserLeague.objects.create(user=user, league_instance=next_league_instance, xp_global=0)
                print(f'user promoted to {next_league} successfully')
                # current_league_instance.userleague_set.filter(user=user).delete()
                return f"{user.username} has been promoted to {next_league.name}"
            except IntegrityError:
                return f"{user.username} is already in the target league instance."

        else:
            print("user is at the highest league level")
            # Handle users in the highest league by reassigning them to another instance of that league
            highest_league_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company__isnull=True, league_end__gt=timezone.now())
                .exclude(id=current_league_instance.id)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not highest_league_instance:
                print(f'No available league instance for highest league {current_league.name}, creating...')
                highest_league_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    max_participants=10
                )

            try:
                UserLeague.objects.create(user=user, league_instance=highest_league_instance, xp_global=0)
                # current_league_instance.userleague_set.filter(user=user).delete()
                print("user has been added to an instance of the highest instance")
                return f"{user.username} has been reassigned within the highest league: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."


def demote_user(user, gems_obtained, current_league_instance):
    with transaction.atomic():
        
        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())

        current_league = current_league_instance.league
        previous_league = League.objects.filter(order__lt=current_league.order).order_by('-order').first()
        print(f"In the demotion view, demoting user {user.username} from curren tleague {current_league}")

        if previous_league:
            print(f" there is a lower league {previous_league}")

            # Find or create an available LeagueInstance for the previous league
            previous_league_instance = (
                LeagueInstance.objects
                .filter(league=previous_league, is_active=True, company__isnull=True, league_end__gt=timezone.now())
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not previous_league_instance:
                print(f'No available league instance for previous league {current_league.name}, creating...')
                previous_league_instance = LeagueInstance.objects.create(
                    league=previous_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    max_participants=10
                )
            try:
                UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp_global=0)
                # Deactivate the current league membership by deleting the current UserLeague entry
                # current_league_instance.userleague_set.filter(user=user).delete()
                return f"{user.username} has been demoted to {previous_league.name}"
            except IntegrityError:
                return f"{user.username} is already in the target league instance."

        else:
            print('there is no lower league level')
            # Handle users in the lowest league by reassigning them to another instance of that league
            lowest_league_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company__isnull=True, league_end__gt=timezone.now())
                .exclude(id=current_league_instance.id)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not lowest_league_instance:
                print("no lower league level instance so creating")
                lowest_league_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    max_participants=10
                )

            try:
                UserLeague.objects.create(user=user, league_instance=lowest_league_instance, xp_global=0)
                # current_league_instance.userleague_set.filter(user=user).delete()
                print(f"{user.username} has been reassigned to another lowest league instance")
                return f"{user.username} has been reassigned within the lowest league: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."


def retain_user(user, gems_obtained, current_league_instance):
    with transaction.atomic():
        # Get the user's current active league
        current_league = current_league_instance.league
        
        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())

        # current_league = current_user_league.league_instance.league
        print(f"In the retaining view, retaining user {user.username} in current league {current_league}")

        # Find or create another active instance of the same league with available slots
        # Find only leagues whose enddate is greater than time.now
        retain_league_instance = (
            LeagueInstance.objects
            .filter(league=current_league, is_active=True, company__isnull=True, league_end__gt=timezone.now())
            .exclude(id=current_league_instance.id)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )

        if retain_league_instance:
            print('Found an existing retain league instance:', retain_league_instance)
        else:
            # Create a new league instance if none found
            retain_league_instance = LeagueInstance.objects.create(
                league=current_league,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(minutes=15),
                max_participants=10
            )
            print('Created new retain league instance:', retain_league_instance)

        # Double-check that the user is not already in the target league instance
        if UserLeague.objects.filter(user=user, league_instance=retain_league_instance).exists():
            print(f"{user.username} is already in the target league instance.")
            return f"{user.username} is already in the target league instance."

        # Attempt to create a new UserLeague entry for the user
        try:
            UserLeague.objects.create(user=user, league_instance=retain_league_instance, xp_global=0)
            # Remove the user from the old league instance
            # current_user_league.delete()
            # current_league_instance.userleague_set.filter(user=user).delete()
            print(f"{user.username} has been retained within the league: {current_league.name}.")
            return f"{user.username} has been retained within the league: {current_league.name}."
        except IntegrityError as e:
            print('IntegrityError encountered:', e)
            return f"{user.username} could not be added to the target league instance due to an IntegrityError."




MIN_USERS_FOR_LEAGUE = 5  # Minimum users to create the first league

def get_highest_company_league_level(company):
    if not company:
        print("No company provided.")
        return 0  # or a suitable default value
    member_count = company.members.count()
    # Determine highest level based on member count, e.g., 1 league per 5 members
    max_level = min(member_count // MIN_USERS_FOR_LEAGUE, League.objects.count())  # Adjust division as needed
    print(max_level)
    return max_level


def promote_company_user(user,gems_obtained, current_league_instance):
    with transaction.atomic():
        print(f'promoting the company user {user.username}')
        current_league = current_league_instance.league
        company = current_league_instance.company
        if company is None:
            print(f"No company associated with the league instance for user {user.username}")
            return f"No company associated with the league instance for user {user.username}"


        # Calculate the highest league level for the company
        highest_company_level = get_highest_company_league_level(company)
        print(f'highest company level {highest_company_level}')
        next_league = League.objects.filter(order__gt=current_league.order, order__lte=highest_company_level).order_by('order').first()

        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())


        if next_league:
            print('found next league.',next_league)
            next_league_instance = (
                LeagueInstance.objects
                .filter(league=next_league, is_active=True, company=company, league_end__gt=timezone.now())
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not next_league_instance:
                next_league_instance = LeagueInstance.objects.create(
                    league=next_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    company=company,
                    max_participants=10
                )

            try:
                UserLeague.objects.create(user=user, league_instance=next_league_instance, xp_company=0)
                # current_league_instance.userleague_set.filter(user=user).delete()
                print('current league instance deleted')
                return f"{user.username} has been promoted to {next_league.name}"
            except IntegrityError:
                return f"{user.username} is already in the target league instance."
        else:
            # If user is in the highest level, reassign to another instance within the same level
            print('user is in the highest level, reassign to another instance within the same level')
            current_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company=company, league_end__gt=timezone.now())
                .exclude(id=current_league_instance.id)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not current_instance:
                current_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    company=company,
                    max_participants=10
                )

            try:
                UserLeague.objects.create(user=user, league_instance=current_instance, xp_company=0)
                # current_league_instance.userleague_set.filter(user=user).delete()
                print('current league instance deleted')
                return f"{user.username} is reassigned within the highest league level: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."



def demote_company_user(user,gems_obtained,  current_league_instance):
    with transaction.atomic():
        print('demoting compamy user')
        current_league = current_league_instance.league
        company = current_league_instance.company

        # Calculate the highest league level for the company
        highest_company_level = get_highest_company_league_level(company)
        previous_league = League.objects.filter(order__lt=current_league.order, order__gte=highest_company_level).order_by('-order').first()

        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())

        if previous_league:
            # current_league_instance.userleague_set.filter(user=user).delete()

            previous_league_instance = (
                LeagueInstance.objects
                .filter(league=previous_league, is_active=True, company=company, league_end__gt=timezone.now())
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not previous_league_instance:
                previous_league_instance = LeagueInstance.objects.create(
                    league=previous_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    company=company,
                    max_participants=10
                )

            UserLeague.objects.create(user=user, league_instance=previous_league_instance, xp_company=0)
            return f"{user.username} has been demoted to {previous_league.name}"
        else:
            # Reassign within the lowest league instance if no lower league exists
            lowest_league_instance = (
                LeagueInstance.objects
                .filter(league=current_league, is_active=True, company=company, league_end__gt=timezone.now())
                .exclude(id=current_league_instance.id)
                .annotate(participant_count=Count('userleague'))
                .filter(participant_count__lt=F('max_participants'))
                .first()
            )

            if not lowest_league_instance:
                lowest_league_instance = LeagueInstance.objects.create(
                    league=current_league,
                    league_start=timezone.now(),
                    league_end=timezone.now() + timezone.timedelta(minutes=15),
                    company=company,
                    max_participants=10
                )

            try:
                UserLeague.objects.create(user=user, league_instance=lowest_league_instance, xp_company=0)
                print(f"User {user.username} demoted to league {lowest_league_instance.league}")
                # current_league_instance.userleague_set.filter(user=user).delete()
                return f"{user.username} is reassigned within the lowest league: {current_league.name}."
            except IntegrityError:
                return f"{user.username} is already in the target league instance."
            

def retain_company_user(user,gems_obtained,  current_league_instance):
    with transaction.atomic():
        print('in the retain company view')
        # Find the user's current active league instance associated with the company
        current_league = current_league_instance.league
        company = current_league_instance.company

        add_manual_gem(user=user, manual_gem_count=gems_obtained, date=timezone.now().date())

        # Find or create another active instance of the same league for the same company with available slots
        retain_league_instance = (
            LeagueInstance.objects
            .filter(league=current_league, is_active=True, company=company, league_end__gt=timezone.now())
            .exclude(id=current_league_instance.id)
            .annotate(participant_count=Count('userleague'))
            .filter(participant_count__lt=F('max_participants'))
            .first()
        )
        print(f'retaining user {user.email}')

        # If no active instance with space is found, create a new one
        if not retain_league_instance:
            retain_league_instance = LeagueInstance.objects.create(
                league=current_league,
                company=company,
                league_start=timezone.now(),
                league_end=timezone.now() + timezone.timedelta(minutes=15),
                max_participants=10
            )

            print('creating new current league as not found')

        # Attempt to create a new UserLeague entry for the user
        try:
            UserLeague.objects.create(user=user, league_instance=retain_league_instance, xp_company=0)
            print(f"User {user.username} reassigned to league {retain_league_instance.league}")
            # current_league_instance.userleague_set.filter(user=user).delete()
            return f"{user.username} has been retained within the company league: {current_league.name}."
        except IntegrityError:
            return f"{user.username} is already in the target company league instance."