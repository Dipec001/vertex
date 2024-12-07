import requests
from django.conf import settings
import time

# Example function to validate Google tokens
def validate_google_token(id_token):
    url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
    
    try:
        response = requests.get(url)
        token_info = response.json()

        if response.status_code != 200:
            return None

        # Check if the audience (aud) matches one of the expected client IDs
        aud = token_info.get('aud')
        # if aud not in [
        #     settings.GOOGLE_WEB_CLIENT_ID,
        #     settings.GOOGLE_IOS_CLIENT_ID,
        #     settings.GOOGLE_ANDROID_CLIENT_ID
        # ]:
        #     raise ValueError("Invalid client ID")

        # Check if the token has expired
        exp = int(token_info.get('exp', 0))
        current_time = int(time.time())
        if exp < current_time:
            raise ValueError("Token has expired")

        # Check if the issuer is Google
        iss = token_info.get('iss')
        if iss not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError("Invalid token issuer")

        # Check if the email is verified
        # email_verified = token_info.get('email_verified', 'false')
        # if email_verified != 'true':
        #     raise ValueError("Email is not verified")

        return token_info  # Token is valid

    except (requests.RequestException, ValueError) as e:
        # You can log the error for debugging purposes
        return None
