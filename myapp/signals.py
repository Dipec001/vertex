from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver

@receiver(social_account_added)
def update_login_type(sender, request, sociallogin, **kwargs):
    user = sociallogin.user
    if sociallogin.account.provider == 'google':
        user.login_type = 'google'
    elif sociallogin.account.provider == 'facebook':
        user.login_type = 'facebook'
    elif sociallogin.account.provider == 'apple':
        user.login_type = 'apple'
    user.save()
