# from celery import shared_task
# from django.utils import timezone
# from datetime import timedelta
# from myapp.models import CustomUser, Xp, Draw
# from fcm_django.models import FCMDevice
# from .models import PushNotificationStatus
# import logging
# from firebase_admin import messaging
# from .utils import send_draw_notification

# logger = logging.getLogger(__name__)

# @shared_task
# def check_and_notify_users():
#     current_utc_time = timezone.now()
#     users = CustomUser.objects.exclude(timezone=None)

#     for user in users:
#         user_local_time = current_utc_time.astimezone(user.timezone)
#         end_of_day = user_local_time.replace(hour=23, minute=59, second=59, microsecond=999999)
#         hours_left = (end_of_day - user_local_time).total_seconds() / 3600

#         if hours_left <= 6:
#             notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type='six_hour')
            
#             if not notification.sent:
#                 previous_xp = Xp.objects.filter(user=user, date=user_local_time.date()).last()
#                 daily_xp = previous_xp.totalXpToday if previous_xp else 0

#                 if daily_xp < 250:
#                     xp_needed = 250 - daily_xp
#                     user_devices = FCMDevice.objects.filter(user=user)
#                     for device in user_devices:
#                         message = messaging.Message(
#                             notification=messaging.Notification(
#                                 title='Keep Your Streak!',
#                                 body=f'To keep your streak of {user.streak} going, you need to earn {xp_needed} more XP - keep going!',
#                             ),
#                             token=device.registration_id
#                         )
#                         response = messaging.send(message)
#                         logger.info(f'Successfully sent message to {device.registration_id}: {response}')
                    
#                     notification.sent = True
#                     notification.save()



# @shared_task
# def notify_gem_reset():
#     now_utc = timezone.now()
    
#     batch_size = 100  # Adjust based on your needs
#     offset = 0

#     while True:
#         users = CustomUser.objects.exclude(timezone=None).values('id', 'email', 'timezone', 'gems_spent')[offset:offset + batch_size]

#         if not users:
#             logger.info("Processed all users successfully.")
#             break

#         for user in users:
#             user_timezone = user['timezone']

#             try:
#                 user_local_time = now_utc.astimezone(user_timezone)
                
#                 # Check if it's Sunday 6 PM in the user's local timezone
#                 if user_local_time.weekday() == 6 and user_local_time.hour == 18:
#                     if user['gems_spent'] > 0:
#                         # Get or create the notification status
#                         notification, created = PushNotificationStatus.objects.get_or_create(user_id=user['id'], notification_type='gem_reset')

#                         if not notification.sent:
#                             user_devices = FCMDevice.objects.filter(user_id=user['id'])
#                             for device in user_devices:
#                                 message = messaging.Message(
#                                     notification=messaging.Notification(
#                                         title='Weekly Gem Reset Reminder',
#                                         body=f'You currently have {user["gems_spent"]} gems to exchange, remember: the weekly reset happens tonight!',
#                                     ),
#                                     token=device.registration_id
#                                 )
#                                 response = messaging.send(message)
#                                 logger.info(f'Successfully sent gem reminder to {device.registration_id}: {response}')
                            
#                             # Mark notification as sent
#                             notification.sent = True
#                             notification.save()

#             except Exception as e:
#                 logger.error(f"Error processing user {user['email']} with timezone {user['timezone']}: {e}")

#         offset += batch_size

#     logger.info("Gem reminder task completed successfully.")


# @shared_task
# def notify_draw_one_day_before():
#     now = timezone.now()
#     draw_time = now + timedelta(days=1, hours=3)
#     draws = Draw.objects.filter(draw_date__date=draw_time.date(), draw_date__hour=draw_time.hour, draw_date__minute=0, is_active=True)

#     for draw in draws:
#         users = CustomUser.objects.filter(entries__draw=draw).distinct()
#         send_draw_notification(users, 'Global Draw Reminder', 'Global draw happens tomorrow! Get your final tickets now.', 'draw_one_day_before')

# @shared_task
# def notify_draw_one_hour_before():
#     now = timezone.now()
#     draw_time = now + timedelta(hours=1)
#     draws = Draw.objects.filter(draw_date__date=draw_time.date(), draw_date__hour=draw_time.hour, draw_date__minute=0, is_active=True)

#     for draw in draws:
#         users = CustomUser.objects.filter(entries__draw=draw).distinct()
#         send_draw_notification(users, 'Global Draw Reminder', 'Global draw happens in one hour! Join us live.', 'draw_one_hour_before')

# @shared_task
# def notify_draw_live():
#     now = timezone.now()
#     draws = Draw.objects.filter(draw_date__lte=now, draw_date__hour=now.hour, draw_date__minute=0, is_active=True)

#     for draw in draws:
#         users = CustomUser.objects.filter(entries__draw=draw).distinct()
#         send_draw_notification(users, 'Global Draw Live', 'Global draw is now live, click here to watch along.', 'draw_live')

#         # Mark the draw as notified for live
#         draw.is_active = False
#         draw.save()
