import requests
from django.conf import settings

# Function to validate Facebook access token
def validate_facebook_token(access_token):
    app_id = settings.FACEBOOK_APP_ID  # Your Facebook app ID
    app_secret = settings.FACEBOOK_APP_SECRET  # Your Facebook app secret
    url = f"https://graph.facebook.com/debug_token?input_token={access_token}&access_token={app_id}|{app_secret}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
        data = response.json()

        # Check if the response contains the necessary fields
        if 'data' in data and data['data'].get('is_valid'):
            user_id = data['data'].get('user_id')
            return user_id
        else:
            raise ValueError("Invalid token.")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request failed: {e}")
    except ValueError as ve:
        raise ve
