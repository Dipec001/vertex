from firebase_admin.messaging import Message, Notification
from fcm_django.models import FCMDevice

Message(
    notification=Notification(title="title", body="text", image="url"),
    topic="Optional topic parameter: Whatever you want",
)

Message(
    data={
        "Nick" : "Mario",
        "body" : "great match!",
        "Room" : "PortugalVSDenmark"
   },
   topic="Optional topic parameter: Whatever you want",
)

# Send bulk messages to all
# You can still use .filter() or any methods that return QuerySet (from the chain)
devices = FCMDevice.objects.all()
devices.send_message(Message(data={...}))

# Subscribing
FCMDevice.objects.all().handle_topic_subscription(True, topic="TOPIC NAME")
device = FCMDevice.objects.all().first()
device.handle_topic_subscription(True, topic="TOPIC NAME")

# Finally you can send a message to that topic
from firebase_admin.messaging import Message
message = Message(..., topic="A topic")
# You can still use .filter() or any methods that return QuerySet (from the chain)
FCMDevice.objects.send_message(message)

# Unsubscribing
FCMDevice.objects.all().handle_topic_subscription(False, topic="TOPIC NAME")
device = FCMDevice.objects.all().first()
device.handle_topic_subscription(False, topic="TOPIC NAME")