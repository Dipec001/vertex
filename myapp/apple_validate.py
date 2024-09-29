import jwt
import requests
from django.conf import settings
from jwt import PyJWKClient
import os

# Function to validate Apple ID token
# def validate_apple_token(id_token):
#     # Fetch Apple's public keys
#     jwks_url = "https://appleid.apple.com/auth/keys"
#     response = requests.get(jwks_url)
#     keys = response.json().get('keys')
#     print(keys)

#     # Decode and verify the ID token
#     try:
#         # Decode the token without verification first to get the header
#         header = jwt.get_unverified_header(id_token)

#         print(header)

#         # Find the correct key
#         for key in keys:
#             if key['kid'] == header['kid']:
#                 public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

#                 # Verify the token
#                 decoded_token = jwt.decode(
#                     id_token,
#                     public_key,
#                     algorithms=['RS256'],
#                     audience=settings.APPLE_CLIENT_ID,  # Your app's client ID
#                     options={"require": ["exp", "iss", "aud"]}
#                 )
#                 return decoded_token

#     except jwt.ExpiredSignatureError:
#         raise ValueError("Token has expired.")
#     except jwt.InvalidTokenError:
#         raise ValueError("Invalid token.")

#     return None

def validate_apple_token(apple_token):
        # Your implementation to verify and decode the Apple token
        try:
            # Use your public key or the Apple public key to verify the signature
            secret_key = os.getenv('client_secret')
            decoded_token = jwt.decode(
                apple_token,
                algorithms='RS256',
                key=secret_key,
                audience=os.getenv('client_id'),
                options={"verify_signature": False},
                issuer='https://appleid.apple.com',)
            return decoded_token
        except Exception as e:
            return None  # Return None instead of str(e) to distinguish from valid decoding

