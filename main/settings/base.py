"""Settings shared by development and production environments."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def env_value(name: str) -> str:
    """Return a required, non-empty environment variable."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    return value


def env_bool(name: str, *, default: bool | None = None) -> bool:
    """Parse a boolean environment variable with strict validation."""
    value = os.environ.get(name)
    if value is None:
        if default is None:
            raise ImproperlyConfigured(f"Set the {name} environment variable.")
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} must be one of: true, false, 1, 0, yes, no, on, off."
    )


def env_int(
    name: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
) -> int:
    """Parse an integer environment variable and enforce an optional minimum."""
    value = os.environ.get(name)
    if value is None:
        if default is None:
            raise ImproperlyConfigured(f"Set the {name} environment variable.")
        parsed = default
    else:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ImproperlyConfigured(f"{name} must be an integer.") from exc

    if minimum is not None and parsed < minimum:
        raise ImproperlyConfigured(f"{name} must be at least {minimum}.")
    return parsed


def env_list(
    name: str,
    *,
    default: list[str] | None = None,
    required: bool = False,
) -> list[str]:
    """Parse a comma-separated environment variable into non-empty values."""
    value = os.environ.get(name)
    values = (
        [item.strip() for item in value.split(",") if item.strip()]
        if value is not None
        else list(default or [])
    )
    if required and not values:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    return values


BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_ROOT = BASE_DIR / "static"

INSTALLED_APPS = [
    "polls.apps.PollsConfig",
    "hosts.apps.HostsConfig",
    "cves.apps.CvesConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "snippets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "main.wsgi.application"
ASGI_APPLICATION = "main.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}
