import requests
from django.conf import settings

# Function to validate Facebook access token
def validate_facebook_token(access_token):
    app_id = settings.FACEBOOK_APP_ID  # Your Facebook app ID
    app_secret = settings.FACEBOOK_APP_SECRET  # Your Facebook app secret
    url = f"https://graph.facebook.com/debug_token?input_token={access_token}&access_token={app_id}|{app_secret}"

    response = requests.get(url)
    data = response.json()

    if 'data' in data and data['data']['is_valid']:
        user_id = data['data']['user_id']
        return user_id
    else:
        raise ValueError("Invalid token.")

