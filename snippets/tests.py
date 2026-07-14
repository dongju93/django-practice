from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from snippets.models import Snippet


class SnippetAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.snippet = Snippet.objects.create(code="print('existing')")
        cls.user = get_user_model().objects.create_user(
            username="snippet-editor",
            password="test-password",
        )
        cls.user.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label="snippets",
                codename__in=[
                    "add_snippet",
                    "change_snippet",
                    "delete_snippet",
                ],
            )
        )

    def setUp(self):
        self.list_url = reverse("snippet-list")
        self.detail_url = reverse("snippet-detail", args=[self.snippet.pk])

    def test_anonymous_user_can_read_snippets(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(self.detail_url).status_code, status.HTTP_200_OK
        )

    def test_anonymous_write_requests_are_forbidden(self):
        requests = [
            self.client.post(self.list_url, {"code": "print('new')"}),
            self.client.put(self.detail_url, {"code": "print('updated')"}),
            self.client.patch(self.detail_url, {"title": "updated"}),
            self.client.delete(self.detail_url),
        ]

        for response in requests:
            with self.subTest(method=response.request["REQUEST_METHOD"]):
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(Snippet.objects.count(), 1)

    def test_authenticated_user_without_model_permission_cannot_create(self):
        user = get_user_model().objects.create_user(username="no-permission")
        self.client.force_authenticate(user=user)

        response = self.client.post(self.list_url, {"code": "print('new')"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Snippet.objects.count(), 1)

    def test_authenticated_user_with_model_permissions_can_crud(self):
        self.client.force_authenticate(user=self.user)

        create_response = self.client.post(
            self.list_url,
            {"title": "new", "code": "print('new')"},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        created_url = reverse("snippet-detail", args=[create_response.data["id"]])
        update_response = self.client.patch(
            created_url,
            {"title": "updated"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["title"], "updated")

        delete_response = self.client.delete(created_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Snippet.objects.filter(pk=create_response.data["id"]).exists())

    def test_malformed_json_returns_bad_request(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url,
            data='{"code":',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_serializer_validation_error_returns_bad_request(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.list_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_unsupported_method_returns_method_not_allowed(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.detail_url, {"code": "print('new')"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_session_authenticated_write_without_csrf_token_is_forbidden(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        self.assertTrue(
            csrf_client.login(
                username=self.user.username,
                password="test-password",
            )
        )

        response = csrf_client.post(
            self.list_url,
            {"code": "print('new')"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
