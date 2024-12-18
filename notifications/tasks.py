from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from myapp.models import CustomUser, Xp, Draw, UserLeague, LeagueInstance
from fcm_django.models import FCMDevice
from .models import PushNotificationStatus
import logging
from firebase_admin import messaging
from .utils import send_draw_notification

logger = logging.getLogger(__name__)

@shared_task
def check_and_notify_users():
    current_utc_time = now()
    users = CustomUser.objects.exclude(timezone=None)

    for user in users:
        # logger.info(f"Processing user: {user.email}")
        user_local_time = current_utc_time.astimezone(user.timezone)
        # logger.info(f"User local time: {user_local_time}")
        end_of_day = user_local_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        # logger.info(f"End of user's day: {end_of_day}")
        hours_left = (end_of_day - user_local_time).total_seconds() / 3600
        # logger.info(f"Hours left in the day: {hours_left:.2f}")

        if hours_left <= 6:
            logger.info("Notifying user with a six-hour reminder.")
            notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type='six_hour')
            
            if not notification.sent:
                previous_xp = Xp.objects.filter(user=user, date=user_local_time.date()).last()
                daily_xp = previous_xp.totalXpToday if previous_xp else 0

                if daily_xp < 250:
                    xp_needed = 250 - daily_xp
                    user_devices = FCMDevice.objects.filter(user=user)
                    for device in user_devices:
                        message = messaging.Message(
                            notification=messaging.Notification(
                                title='Keep Your Streak!',
                                body=f'To keep your streak of {user.streak} going, you need to earn {xp_needed} more XP - keep going!',
                            ),
                            token=device.registration_id
                        )
                        response = messaging.send(message)
                        logger.info(f'Successfully sent message to {device.registration_id}: {response}')
                    
                    notification.sent = True
                    notification.save()



@shared_task
def notify_gem_reset():
    now_utc = now()
    
    batch_size = 100  # Adjust based on your needs
    offset = 0

    while True:
        users = CustomUser.objects.exclude(timezone=None)[offset:offset + batch_size]

        if not users:
            logger.info("Processed all users successfully.")
            break

        for user in users:
            user_timezone = user.timezone

            try:
                user_local_time = now_utc.astimezone(user_timezone)
                
                # Check if it's Sunday 6 PM in the user's local timezone
                if user_local_time.weekday() == 6 and user_local_time.hour == 18:
                    gem_count = user.get_gem_count()
                    # logger.info(f"Gem count for {user.email}: {gem_count}")
                    if gem_count > 0:
                        # Get or create the notification status
                        notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type='gem_reset')

                        if not notification.sent:
                            user_devices = FCMDevice.objects.filter(user=user)
                            for device in user_devices:
                                message = messaging.Message(
                                    notification=messaging.Notification(
                                        title='Weekly Gem Reset Reminder',
                                        body=f'You currently have {gem_count} gems to exchange, remember: the weekly reset happens tonight!',
                                    ),
                                    token=device.registration_id
                                )
                                response = messaging.send(message)
                                logger.info(f'Successfully sent gem reminder to {device.registration_id}: {response}')
                            
                            # Mark notification as sent
                            notification.sent = True
                            notification.save()

            except Exception as e:
                logger.error(f"Error processing user {user.email} with timezone {user.timezone}: {e}")

        offset += batch_size

    logger.info("Gem reminder task completed successfully.")


@shared_task
def notify_draw_one_day_before():
    now = now()
    draw_time = now + timedelta(days=1, hours=3)
    draws = Draw.objects.filter(draw_date__date=draw_time.date(), draw_date__hour=draw_time.hour, draw_date__minute=0, is_active=True)

    for draw in draws:
        users = CustomUser.objects.filter(entries__draw=draw).distinct()
        send_draw_notification(users, 'Global Draw Reminder', 'Global draw happens tomorrow! Get your final tickets now.', 'draw_one_day_before')

@shared_task
def notify_draw_one_hour_before():
    now = now()
    draw_time = now + timedelta(hours=1)
    draws = Draw.objects.filter(draw_date__date=draw_time.date(), draw_date__hour=draw_time.hour, draw_date__minute=0, is_active=True)

    for draw in draws:
        users = CustomUser.objects.filter(entries__draw=draw).distinct()
        send_draw_notification(users, 'Global Draw Reminder', 'Global draw happens in one hour! Join us live.', 'draw_one_hour_before')

@shared_task
def notify_draw_live():
    now = now()
    draws = Draw.objects.filter(draw_date__lte=now, draw_date__hour=now.hour, draw_date__minute=0, is_active=True)

    for draw in draws:
        users = CustomUser.objects.filter(entries__draw=draw).distinct()
        send_draw_notification(users, 'Global Draw Live', 'Global draw is now live, click here to watch along.', 'draw_live')

        # Mark the draw as notified for live
        draw.is_active = False
        draw.save()



@shared_task
def notify_closest_relegation():
    today = now()

    league_instances = LeagueInstance.objects.filter(is_active=True, league_end__date=today.date())

    for league_instance in league_instances:
        if league_instance.company:
            user_leagues = UserLeague.objects.filter(league_instance=league_instance).order_by('xp_company')
        else:
            user_leagues = UserLeague.objects.filter(league_instance=league_instance).order_by('xp_global')

        total_users = user_leagues.count()
        demotion_threshold = int(total_users * 0.80)

        for index, user_league in enumerate(user_leagues):
            if index == demotion_threshold - 1:  # Just above the relegation zone
                user = user_league.user
                user_local_time = today.astimezone(user.timezone)

                if user_local_time.weekday() == 6:
                    notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type='relegation_warning')

                    if not notification.sent:
                        user_devices = FCMDevice.objects.filter(user=user)
                        for device in user_devices:
                            message = messaging.Message(
                                notification=messaging.Notification(
                                    title='Stay Active!',
                                    body="You’re one position away from relegation, let’s make today an active one!",
                                ),
                                token=device.registration_id
                            )
                            response = messaging.send(message)
                            logger.info(f'Successfully sent relegation warning to {user.email}: {response}')

                        notification.sent = True
                        notification.save()



@shared_task
def notify_closest_promotion():
    today = now()

    league_instances = LeagueInstance.objects.filter(is_active=True, league_end__date=today.date())

    for league_instance in league_instances:
        if league_instance.company:
            user_leagues = UserLeague.objects.filter(league_instance=league_instance).order_by('-xp_company')
        else:
            user_leagues = UserLeague.objects.filter(league_instance=league_instance).order_by('-xp_global')

        total_users = user_leagues.count()
        promotion_threshold = int(total_users * 0.30)

        for index, user_league in enumerate(user_leagues):
            if index == promotion_threshold:  # Just below the promotion zone
                user = user_league.user
                user_local_time = today.astimezone(user.timezone)

                if user_local_time.weekday() == 6:
                    notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type='promotion_warning')

                    if not notification.sent:
                        user_devices = FCMDevice.objects.filter(user=user)
                        for device in user_devices:
                            message = messaging.Message(
                                notification=messaging.Notification(
                                    title='Stay on Top!',
                                    body="There’s someone closing in on your promotion place! Stay active to keep your promotion.",
                                ),
                                token=device.registration_id
                            )
                            response = messaging.send(message)
                            logger.info(f'Successfully sent promotion warning to {user.email}: {response}')

                        notification.sent = True
                        notification.save()
