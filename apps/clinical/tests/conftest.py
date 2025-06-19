import pytest
from django.conf import settings

@pytest.fixture(autouse=True)
def set_test_urls(settings):
    settings.ROOT_URLCONF = 'hms_config.urls'  # <-- or whatever your root urls.py is
