from django.db.models.signals import post_save
from django.dispatch import receiver
from fcm_django.models import FCMDevice
from firebase_admin import messaging
from myapp.models import Streak, Xp
from .models import PushNotificationStatus
import logging

# Setting up logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=FCMDevice)
def subscribe_to_topic(sender, instance, created, **kwargs):
    """Add users all userstopic"""
    if created:
        registration_id = instance.registration_id
        messaging.subscribe_to_topic([registration_id], 'users_topic')
        print(f'Successfully subscribed {registration_id} to the topic.')


@receiver(post_save, sender=Streak)
def notify_streak(sender, instance, **kwargs):
    """Send streak achievement notification"""
    logger.info("streak acheivement signal triggered")
    print(instance.currentStreak)
    print(instance.timeStamp)
    try:
        # Check if the current streak is a multiple of 5
        if instance.currentStreak > 0 and instance.currentStreak % 5 == 0:
            print("it's done")
            user_devices = FCMDevice.objects.filter(user=instance.user)
            for device in user_devices:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title='Congratulations!',
                        body=f'Well done on reaching your streak of {instance.currentStreak} days!',
                    ),
                    token=device.registration_id,
                )
                response = messaging.send(message)
                logger.info(f'Successfully sent message: {response}')
    except Exception as e:
        logger.error(f'Error sending notification: {str(e)}')


@receiver(post_save, sender=Xp)
def notify_streak_maintenance(sender, instance, **kwargs):
    """ THis signal sends notification to the user to inform them of their streak maintenance"""
    try:
        if instance.totalXpToday >= 200 and instance.totalXpToday < 250:
            
            xp_needed = 250 - instance.totalXpToday
            notification, created = PushNotificationStatus.objects.get_or_create(user=instance.user, notification_type='streak')
            
            if not notification.sent:
                user_devices = FCMDevice.objects.filter(user=instance.user)
                for device in user_devices:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title='Keep Your Streak!',
                            body=f'To keep your streak of {instance.user.streak} going, you need to earn {xp_needed} more XP - keep going!',
                        ),
                        token=device.registration_id
                    )
                    response = messaging.send(message)
                    logger.info(f'Successfully sent message to {device.registration_id}: {response}')
                
                notification.sent = True
                notification.save()
    except Exception as e:
        logger.error(f'Error sending notification: {str(e)}')
