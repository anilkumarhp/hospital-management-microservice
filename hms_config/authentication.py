# hms_config/authentication.py
import jwt
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions

class CustomJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # Get the 'Authorization' header from the incoming request
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != b'bearer':
            # No token provided, or incorrect scheme
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(auth_header) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            # Decode the token using the secret key
            token = auth_header[1].decode('utf-8')
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token.')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentication error: {e}')

        try:
            # Fetch our local user based on the user_id from the token payload
            user_id = payload['user_id']
            user = User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No user matching this token was found.')
        except KeyError:
            raise exceptions.AuthenticationFailed('Token is missing user_id payload.')

        # The contract for a successful authentication is to return (user, auth).
        # We don't have a separate token object, so the second element is None.
        return (user, None)