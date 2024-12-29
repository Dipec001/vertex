from django.core.management.base import BaseCommand
from myapp.models import Feed, CustomUser, Clap
import random
from datetime import datetime

class Command(BaseCommand):
    help = 'Add 60 mock feeds for a user he\'s following and clap by user 9'

    def handle(self, *args, **kwargs):
        user_id = 6  # User ID for the user he's following
        clap_user = CustomUser.objects.get(id=9)
        user = CustomUser.objects.get(id=user_id)
        
        feed_types = [Feed.PROMOTION, Feed.MILESTONE, Feed.STREAK, Feed.PRIZE, Feed.ACTIVITY_MOVEMENT]

        for _ in range(60):
            feed = Feed.objects.create(
                user=user,
                feed_type=random.choice(feed_types),
                feed_detail="Mock feed detail",
                content="Mock feed content",
                created_at=datetime.now(),
                claps_count=0
            )
            # Add a clap for user 9
            Clap.objects.create(user=clap_user, feed=feed)

        self.stdout.write(self.style.SUCCESS('Successfully added 60 mock feeds for the user he\'s following with claps by user 9'))
