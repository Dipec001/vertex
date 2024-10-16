from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Xp, Streak, Company, Draw

@receiver(post_save, sender=Xp)
def update_streak_on_xp_change(sender, instance, **kwargs):
    print("Signal triggered")
    user = instance.user
    total_xp_today = instance.totalXpToday
    print(f"Total XP today: {total_xp_today}")

    # Check if total XP for today is >= 500
    if total_xp_today < 500:
        print("Total XP is less than 500, not updating streak")
        return

    current_date = timezone.now().date()

    # Check if a streak record exists for today
    streak_record = Streak.objects.filter(user=user, timeStamp__date=current_date).first()

    # If a streak record exists for today, exit
    if streak_record:
        print("Streak record already exists for today, exiting")
        return  # Streak has already been updated today

    # Check for a previous streak record from yesterday
    previous_date = current_date - timezone.timedelta(days=1)
    previous_streak_record = Streak.objects.filter(user=user, timeStamp__date=previous_date).first()

    if previous_streak_record:
        # If a previous record exists, get the current and highest streak values
        current_streak = previous_streak_record.currentStreak
        highest_streak = previous_streak_record.highestStreak
        print("Previous streak record found, using existing values")
    else:
        # If no previous record, initialize current streak to 0 and highest streak to 0
        current_streak = 0
        highest_streak = 0
        print("No previous streak record found, initializing to zero")

    # Create a new streak record for today
    streak_record = Streak.objects.create(
        user=user,
        currentStreak=current_streak + 1,  # Increment the current streak by 1
        highestStreak=max(highest_streak, current_streak + 1),  # Update highest streak if necessary
        timeStamp=timezone.now()  # Set the current timestamp
    )
    
    # Update the streak in the CustomUser model
    user.streak += 1  # Increment the streak by 1
    user.save()  # Save the changes to the CustomUser model

    print("Streak record created and updated")


@receiver(post_save, sender=Company)
def create_company_draw(sender, instance, created, **kwargs):
    if created:
        # Schedule draw for the 1st of the next month
        today = timezone.now()
        first_of_next_month = (today.replace(day=1) + timezone.timedelta(days=32)).replace(day=1)

        # Create company draw
        Draw.objects.create(
            name=f"{instance.name} Company Draw",
            draw_type='company',
            draw_date=first_of_next_month,
            number_of_winners=5,  # Example number of winners
            is_active=True,
            company=instance
        )