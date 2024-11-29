from myapp.models import Gem

def add_manual_gem(user, manual_gem_count, date):
    gem, created = Gem.objects.get_or_create(user=user, date=date)
    # Ensure manual_gem is not None before adding
    if gem.manual_gem is None:
        gem.manual_gem = 0  # Initialize to 0 if it's None
    gem.manual_gem += manual_gem_count  # Increment the manual gems
    gem.copy_manual_gem += manual_gem_count
    gem.save()
