from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Xp, Streak, DrawWinner, League, UserLeague, LeagueInstance, Feed, Gem
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver


@receiver(post_save, sender=Xp)
def broadcast_global_league_ranking_update(sender, instance, **kwargs):
    user = instance.user

    # Get the user's active global league instance
    user_league = (
        UserLeague.objects
        .filter(user=user, league_instance__is_active=True, league_instance__company__isnull=True)
        .select_related('league_instance', 'user')
        .first()
    )

    if not user_league:
        return  # No active global league found, exit early

    league_instance = user_league.league_instance

    # Fetch all users in the league and calculate rankings
    rankings = UserLeague.objects.filter(
        league_instance=league_instance
    ).select_related('user').order_by('-xp_global', 'id')

    total_users = rankings.count()
    promotion_threshold = int(total_users * 0.30)  # Top 30%
    demotion_threshold = int(total_users * 0.80)  # Bottom 20%

    rankings_data = []
    for index, ul in enumerate(rankings, start=1):
        # Determine advancement status
        if total_users <= 3:
            if ul.xp_global == 0:
                advancement = "Demoted"
                gems_obtained = 0
            else:
                advancement = "Retained"
                gems_obtained = 10
        else:
            if index <= promotion_threshold:
                gems_obtained = 20 - (index - 1) * 2  # Reward for promotion
                advancement = "Promoted"
            elif index <= demotion_threshold:
                gems_obtained = 10  # Retained users get a base reward
                advancement = "Retained"
            else:
                gems_obtained = 0  # Demoted users receive no gems
                advancement = "Demoted"

        # Prefix for S3 bucket URL
        s3_bucket_url = "https://video-play-api-bucket.s3.amazonaws.com/"

        # User data for each ranking
        rankings_data.append({
            "user_id": ul.user.id,
            "username": ul.user.username,
            "profile_picture": f"{s3_bucket_url}{ul.user.profile_picture}" if ul.user.profile_picture else None,
            "xp": ul.xp_global,
            "streaks": ul.user.streak,
            "gems_obtained": gems_obtained,
            "rank": index,
            "advancement": advancement,
        })

    # Find the current user's rank
    user_rank = next((index for index, r in enumerate(rankings_data, start=1) if r["user_id"] == user.id), None)

    # Prepare data to send
    data = {
        "league_name": league_instance.league.name,
        "league_level": 11 - league_instance.league.order,
        "league_start": league_instance.league_start.isoformat(),
        "league_end": league_instance.league_end.isoformat(),
        "user_rank": user_rank,
        "rankings": rankings_data,
    }

    # Send the data to the WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'league_{league_instance.id}',
        {
            'type': 'send_league_update',
            'data': data,
        }
    )


@receiver(post_save, sender=Xp)
def broadcast_company_league_ranking_update(sender, instance, **kwargs):
    user = instance.user

    # Get the user's active company league instance
    user_league = (
        UserLeague.objects
        .filter(user=user, league_instance__is_active=True, league_instance__company__isnull=False)
        .select_related('league_instance', 'user')
        .first()
    )

    if not user_league:
        return  # No active company league found, exit early

    league_instance = user_league.league_instance

    # Fetch all users in the league and calculate rankings
    rankings = UserLeague.objects.filter(
        league_instance=league_instance
    ).select_related('user').order_by('-xp_company', 'id')

    total_users = rankings.count()
    promotion_threshold = int(total_users * 0.30)  # Top 30%
    demotion_threshold = int(total_users * 0.80)  # Bottom 20%

    rankings_data = []
    for index, ul in enumerate(rankings, start=1):
        # Determine advancement status
        if total_users <= 3:
            if ul.xp_company == 0:
                advancement = "Demoted"
                gems_obtained = 0
            else:
                advancement = "Retained"
                gems_obtained = 10
        else:
            if index <= promotion_threshold:
                gems_obtained = 20 - (index - 1) * 2  # Reward for promotion
                advancement = "Promoted"
            elif index <= demotion_threshold:
                gems_obtained = 10  # Retained users get a base reward
                advancement = "Retained"
            else:
                gems_obtained = 0  # Demoted users receive no gems
                advancement = "Demoted"

        # Prefix for S3 bucket URL
        s3_bucket_url = "https://video-play-api-bucket.s3.amazonaws.com/"

        # User data for each ranking
        rankings_data.append({
            "user_id": ul.user.id,
            "username": ul.user.username,
            "profile_picture": f"{s3_bucket_url}{ul.user.profile_picture}" if ul.user.profile_picture else None,
            "xp": ul.xp_company,
            "streaks": ul.user.streak,
            "gems_obtained": gems_obtained,
            "rank": index,
            "advancement": advancement,
        })

    # Find the current user's rank
    user_rank = next((index for index, r in enumerate(rankings_data, start=1) if r["user_id"] == user.id), None)

    # Prepare data to send
    data = {
        "league_name": league_instance.league.name,
        "league_level": 11 - league_instance.league.order,
        "league_start": league_instance.league_start.isoformat(),
        "league_end": league_instance.league_end.isoformat(),
        "user_rank": user_rank,
        "rankings": rankings_data,
    }

    # Send the data to the WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'league_{league_instance.id}',
        {
            'type': 'send_league_update',
            'data': data,
        }
    )



@receiver(post_save, sender=Streak)
def broadcast_streak_update(sender, instance, **kwargs):
    user = instance.user
    streak_count = instance.currentStreak

    # Send the updated streak count to the user's WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'streak_{user.id}',  # Create a unique group for each user
        {
            'type': 'send_streak_update',
            'streak_count': streak_count,
        }
    )


@receiver(post_save, sender=Gem)
def broadcast_gem_update(sender, instance, **kwargs):
    user = instance.user
    new_gem_count = user.get_gem_count()  # Use the `get_gem_count` method to get the total gems

    # Get the channel layer and send the updated gem count to the WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'gem_{user.id}',  # Group name based on user_id
        {
            'type': 'send_gem_update',
            'gem_count': new_gem_count,  # Send the new gem count
        }
    )


@receiver(post_save, sender=Feed)
def broadcast_feed_update(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    user_group_name = f'feed_user_{instance.user.id}'
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            'type': 'send_feed_update',
            'feed_type': instance.feed_type,
            'content': instance.content,
            'created_at': str(instance.created_at),
            'claps_count': instance.claps_count,
        }
    )

    if instance.user.company:
        company_group_name = f'feed_company_{instance.user.company.id}'
        async_to_sync(channel_layer.group_send)(
            company_group_name,
            {
                'type': 'send_feed_update',
                'feed_type': instance.feed_type,
                'content': instance.content,
                'created_at': str(instance.created_at),
                'claps_count': instance.claps_count,
            }
        )


@receiver(post_save, sender=DrawWinner)
def broadcast_draw_winner(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    group_name = f'draw_{instance.draw.id}'

    print('winners group', group_name)

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_draw_update',
            'winner': instance.user.username,
            'prize': instance.prize.name if instance.prize else "No Prize",
            'draw_name': instance.draw.draw_name,
            'draw_type': instance.draw.draw_type,
            'draw_date': str(instance.draw.draw_date),
        }
    )
