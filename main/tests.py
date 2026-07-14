import warnings

from django.contrib.auth import get_user_model
from django.core.paginator import UnorderedObjectListWarning
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


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
