"""Local development settings."""

# Django settings modules intentionally re-export every uppercase base setting.
# pylint: disable=wildcard-import,unused-wildcard-import

import os
import secrets

from .base import *  # noqa: F403
from .base import env_bool, env_list

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip() or secrets.token_urlsafe(
    50
)
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "[::1]", "testserver"],
)

if DEBUG:
    INTERNAL_IPS = env_list("DJANGO_INTERNAL_IPS", default=["127.0.0.1"])
    INSTALLED_APPS.insert(  # noqa: F405
        INSTALLED_APPS.index("django.contrib.staticfiles"),  # noqa: F405
        "whitenoise.runserver_nostatic",
    )
    INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
