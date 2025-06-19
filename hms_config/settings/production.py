from .base import *
import os

DEBUG = False

# This will be the IP address or domain name of our server.
# We get this after we launch the EC2 instance.
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# Use WhiteNoise for serving static files
# http://whitenoise.evans.io/en/stable/django.html
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    # ... (Your S3 configuration for media files remains the same)
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}