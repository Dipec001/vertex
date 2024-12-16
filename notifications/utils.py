from .models import PushNotificationStatus
from fcm_django.models import FCMDevice
from firebase_admin import messaging
import logging

logger = logging.getLogger(__name__)

def send_notification(user, title, body, notification_type):
    try:
        notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type=notification_type)
        
        if not notification.sent:
            user_devices = FCMDevice.objects.filter(user=user)
            for device in user_devices:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=device.registration_id
                )
                response = messaging.send(message)
                logger.info(f'Successfully sent message to {device.registration_id}: {response}')
            
            notification.sent = True
            notification.save()
    except Exception as e:
        logger.error(f'Error sending notification to {user.email}: {str(e)}')


def send_draw_notification(users, title, body, notification_type):
    for user in users:
        try:
            notification, created = PushNotificationStatus.objects.get_or_create(user=user, notification_type=notification_type)
            
            if not notification.sent:
                user_devices = FCMDevice.objects.filter(user=user)
                for device in user_devices:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                        ),
                        token=device.registration_id
                    )
                    response = messaging.send(message)
                    logger.info(f'Successfully sent message to {device.registration_id}: {response}')
                
                notification.sent = True
                notification.save()
        except Exception as e:
            logger.error(f'Error sending notification to {user.email}: {str(e)}')