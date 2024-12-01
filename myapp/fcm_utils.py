from firebase_admin.messaging import Message, Notification
from fcm_django.models import FCMDevice

def send_notification_to_all(title, body, data=None, image_url=None):
    """
    Sends a notification to all registered devices.
    """
    devices = FCMDevice.objects.all()
    if not devices.exists():
        return {"success": False, "message": "No devices found."}

    notification = Notification(title=title, body=body, image=image_url)
    message = Message(notification=notification, data=data or {})
    response = devices.send_message(message)

    return {"success": True, "response": response}


def send_notification_to_topic(topic, title, body, data=None, image_url=None):
    """
    Sends a notification to a specific topic.
    """
    notification = Notification(title=title, body=body, image=image_url)
    message = Message(notification=notification, data=data or {}, topic=topic)

    # This part assumes that the devices are already subscribed to the topic
    devices = FCMDevice.objects.filter(active=True)
    if not devices.exists():
        return {"success": False, "message": "No devices subscribed to the topic."}

    response = devices.send_message(message)
    return {"success": True, "response": response}


def subscribe_device_to_topic(device_id, topic):
    """
    Subscribes a device to a topic.
    """
    device = FCMDevice.objects.filter(id=device_id).first()
    if not device:
        return {"success": False, "message": "Device not found."}

    device.handle_topic_subscription(True, topic=topic)
    return {"success": True, "message": f"Device subscribed to topic '{topic}'."}



def unsubscribe_device_from_topic(device_id, topic):
    """
    Unsubscribes a device from a topic.
    """
    device = FCMDevice.objects.filter(id=device_id).first()
    if not device:
        return {"success": False, "message": "Device not found."}

    device.handle_topic_subscription(False, topic=topic)
    return {"success": True, "message": f"Device unsubscribed from topic '{topic}'."}

