import importlib
import os
import warnings
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.core.paginator import UnorderedObjectListWarning
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# `check --deploy` rejects short, low-entropy keys, so this fixture has to look
# like a real key even though it never leaves the test process.
TEST_SECRET_KEY = "kf3s-9q2v-test-only-secret-P7xW1zR8mB4nD6tY0uH5jL2cA_e"

SECURE_PRODUCTION_ENV = {
    "DJANGO_SECRET_KEY": TEST_SECRET_KEY,
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "example.com,www.example.com",
    "DJANGO_SESSION_COOKIE_SECURE": "true",
    "DJANGO_CSRF_COOKIE_SECURE": "true",
    "DJANGO_SECURE_SSL_REDIRECT": "true",
    "DJANGO_SECURE_HSTS_SECONDS": "31536000",
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
    "DJANGO_SECURE_HSTS_PRELOAD": "true",
}

# Only the settings production.py is responsible for. Copying the whole module
# (INSTALLED_APPS, MIDDLEWARE, ...) over the running test configuration would
# swap the app registry mid-run; the deployment security checks read exactly
# these names.
DEPLOY_SETTING_NAMES = (
    "SECRET_KEY",
    "DEBUG",
    "ALLOWED_HOSTS",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
    "SECURE_PROXY_SSL_HEADER",
)


def load_production_settings(**env_overrides):
    """Re-execute main.settings.production against a controlled environment.

    The module reads os.environ at import time, so the only way to test how it
    reacts to a given deployment configuration is to import it again under that
    environment. `load_env_file` is stubbed out because a developer's local
    .env.production must not decide whether this test passes.
    """
    env = {**SECURE_PRODUCTION_ENV, **env_overrides}
    env = {key: value for key, value in env.items() if value is not None}

    module = importlib.import_module("main.settings.production")
    with (
        mock.patch.dict(os.environ, env, clear=True),
        mock.patch("main.settings.base.load_env_file"),
    ):
        return importlib.reload(module)


class ProductionSettingsDeployCheckTests(SimpleTestCase):
    """P1-4 regression: a correctly configured production run has 0 warnings.

    `python manage.py check --deploy` is the gate this pins. It is scoped to
    the `security` tag so unrelated app checks cannot turn a deployment
    regression into a passing test — or vice versa.
    """

    def _run_deploy_checks(self, settings_module):
        overrides = {
            name: getattr(settings_module, name)
            for name in DEPLOY_SETTING_NAMES
            if hasattr(settings_module, name)
        }
        with override_settings(**overrides):
            call_command(
                "check",
                deploy=True,
                fail_level="WARNING",
                tags=["security"],
                verbosity=0,
            )

    def test_secure_production_environment_passes_deploy_checks(self):
        self._run_deploy_checks(load_production_settings())

    def test_production_settings_read_security_values_from_the_environment(self):
        settings_module = load_production_settings()

        self.assertEqual(settings_module.SECRET_KEY, TEST_SECRET_KEY)
        self.assertIs(settings_module.DEBUG, False)
        self.assertEqual(
            settings_module.ALLOWED_HOSTS, ["example.com", "www.example.com"]
        )
        self.assertIs(settings_module.SECURE_SSL_REDIRECT, True)
        self.assertEqual(settings_module.SECURE_HSTS_SECONDS, 31536000)

    def test_insecure_production_environment_fails_deploy_checks(self):
        # Negative control: without it, a check run that silently stopped
        # reporting anything would still look like a pass above.
        settings_module = load_production_settings(
            DJANGO_DEBUG="true",
            DJANGO_SESSION_COOKIE_SECURE="false",
            DJANGO_CSRF_COOKIE_SECURE="false",
            DJANGO_SECURE_SSL_REDIRECT="false",
            DJANGO_SECURE_HSTS_SECONDS="0",
            DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS="false",
            DJANGO_SECURE_HSTS_PRELOAD="false",
        )

        with self.assertRaises(SystemCheckError):
            self._run_deploy_checks(settings_module)

    def test_proxy_ssl_header_is_opt_in(self):
        # Trusting X-Forwarded-Proto by default would let a client fake HTTPS,
        # so the header is only honoured when explicitly enabled.
        default_settings = load_production_settings()
        self.assertFalse(hasattr(default_settings, "SECURE_PROXY_SSL_HEADER"))

        trusted_settings = load_production_settings(
            DJANGO_TRUST_X_FORWARDED_PROTO="true"
        )
        self.assertEqual(
            trusted_settings.SECURE_PROXY_SSL_HEADER,
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )


class ProductionSettingsEnvironmentTests(SimpleTestCase):
    """Misconfiguration must stop the process, not fall back to a dev default."""

    def test_missing_secret_key_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_SECRET_KEY=None)

    def test_missing_allowed_hosts_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_ALLOWED_HOSTS=None)

    def test_blank_allowed_hosts_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_ALLOWED_HOSTS=" , ")

    def test_missing_security_toggle_raises(self):
        # These have no default on purpose: HTTPS-dependent settings should be
        # turned on deliberately, after the proxy and certificate are in place.
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_SECURE_SSL_REDIRECT=None)

    def test_unparsable_boolean_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_CSRF_COOKIE_SECURE="maybe")

    def test_negative_hsts_seconds_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_SECURE_HSTS_SECONDS="-1")


class UserAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        cls.user = user_model.objects.create_user(
            username="regular-user",
            email="user@example.com",
            password="test-password",
        )
        cls.second_admin = user_model.objects.create_superuser(
            username="second-admin",
            email="second-admin@example.com",
            password="test-password",
        )

    def setUp(self):
        self.list_url = reverse("user-list")

    def test_anonymous_user_cannot_list_users(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_cannot_list_users(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_list_is_ordered_and_excludes_sensitive_fields(self):
        self.client.force_authenticate(user=self.admin)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UnorderedObjectListWarning)
            response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [user["username"] for user in response.data["results"]],
            ["admin", "regular-user", "second-admin"],
        )
        for user in response.data["results"]:
            self.assertEqual(set(user), {"url", "username"})
