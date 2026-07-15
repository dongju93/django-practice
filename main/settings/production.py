"""Production settings loaded exclusively from explicit environment values."""

# Django settings modules intentionally re-export every uppercase base setting.
# pylint: disable=wildcard-import,unused-wildcard-import

from .base import *  # noqa: F403
from .base import BASE_DIR, env_bool, env_int, env_list, env_value, load_env_file

# Optional file for local/prod-like runs (e.g. uWSGI). Already-exported vars win.
load_env_file(BASE_DIR / ".env.production")

SECRET_KEY = env_value("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", required=True)

# Keep these values explicit so HTTPS and HSTS can be enabled only after the
# reverse proxy and certificate configuration have been verified.
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT")
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", minimum=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD")

# Trust this header only when a controlled proxy removes client-supplied values
# and sets X-Forwarded-Proto itself.
if env_bool("DJANGO_TRUST_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
