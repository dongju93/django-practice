import json
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import HostIP

XSS_PAYLOAD = '<img src=x onerror="document.body.dataset.pwned=1">'

# hosts/static/hosts/index.js renders the table with DataTables (serverSide).
# DataTables inserts column data with .html() unless a column supplies its own
# renderer, so any user-controlled column without DataTable.render.text() is a
# stored-XSS sink regardless of what the server does with the string. These
# columns hold user input and MUST keep an explicit text renderer.
TEXT_RENDERED_FIELDS = [
    "hostname",
    "ip_address",
    "description",
    "created_at",
    "updated_at",
]


class HostIPStoredXSSTests(TestCase):
    """
    P0-1 regression: HostIP.hostname/description are stored and served as-is.

    The fix lives client-side (DataTables render: DataTable.render.text()),
    so the server is expected to pass the raw payload through unchanged —
    sanitizing or encoding it at write time would corrupt legitimate data
    and only masks the real bug if the client renderer regresses. These
    tests pin that contract and guard the client renderer separately.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="password123"
        )
        # These endpoints now require hosts.view_hostip (P1-2). The XSS
        # contract is about what an authorized reader receives, so grant the
        # read permission and keep the focus on the response body.
        self.user.user_permissions.add(Permission.objects.get(codename="view_hostip"))
        self.client.force_login(self.user)

    def test_data_endpoint_returns_hostname_and_description_unmodified(self):
        host = HostIP.objects.create(
            hostname=XSS_PAYLOAD,
            ip_address="10.0.0.1",
            description=XSS_PAYLOAD,
        )

        response = self.client.post(
            reverse("hosts:data"),
            {
                "draw": 1,
                "start": 0,
                "length": 25,
                "search[value]": "",
                "order[0][column]": 0,
                "order[0][dir]": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        row = next(row for row in response.json()["data"] if row["id"] == host.id)
        self.assertEqual(row["hostname"], XSS_PAYLOAD)
        self.assertEqual(row["description"], XSS_PAYLOAD)

    def test_detail_endpoint_returns_hostname_and_description_unmodified(self):
        host = HostIP.objects.create(
            hostname=XSS_PAYLOAD,
            ip_address="10.0.0.2",
            description=XSS_PAYLOAD,
        )

        response = self.client.get(reverse("hosts:detail", args=[host.id]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hostname"], XSS_PAYLOAD)
        self.assertEqual(data["description"], XSS_PAYLOAD)


class HostTableRendererGuardTests(TestCase):
    """
    Static guard against re-introducing the DataTables HTML-sink columns.

    A column without an explicit renderer falls back to DataTables' default
    .html() insertion. This does not execute index.js or a browser — it only
    proves the required renderer is still wired to each vulnerable column, so
    a future edit that drops `render: DataTable.render.text()` fails CI.
    """

    def setUp(self):
        index_js = Path(__file__).resolve().parent / "static" / "hosts" / "index.js"
        self.source = index_js.read_text(encoding="utf-8")

    def test_user_controlled_columns_use_text_renderer(self):
        for field in TEXT_RENDERED_FIELDS:
            pattern = (
                r'\{\s*data:\s*"%s"[^}]*render:\s*DataTable\.render\.text\(\)'
                % re.escape(field)
            )
            self.assertRegex(
                self.source,
                pattern,
                f'Column "{field}" must render with DataTable.render.text() '
                "to stay safe against stored XSS.",
            )


class HostIPAuthorizationTests(TestCase):
    """
    P1-2 regression: HostIP CRUD endpoints enforce per-action model
    permissions, not just authentication.

    Policy: access is gated by Django's default model permissions —
    view_hostip (read), add_hostip (create), change_hostip (update),
    delete_hostip (delete). A logged-in user without the matching
    permission must be blocked. This is intentionally NOT a shared-editing
    model: authentication alone grants nothing.

    The Ajax/JSON endpoints answer a denied request with a 403 JSON body
    ({"success": false, ...}), so the client's error handler reads the same
    shape it gets from a 400.
    """

    @classmethod
    def setUpTestData(cls):
        cls.host = HostIP.objects.create(
            hostname="web01", ip_address="10.0.0.1", description="prod"
        )

    def _make_user(self, username, *codenames):
        user = get_user_model().objects.create_user(
            username=username, password="password123"
        )
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename))
        return user

    # ---- denied: logged in but missing the required permission ----------

    def test_list_page_denied_without_view_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.get(reverse("hosts:index"))
        self.assertEqual(response.status_code, 403)

    def test_data_endpoint_denied_without_view_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.post(reverse("hosts:data"), {"draw": 1})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])

    def test_detail_endpoint_denied_without_view_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.get(reverse("hosts:detail", args=[self.host.id]))
        self.assertEqual(response.status_code, 403)

    def test_create_denied_without_add_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.post(
            reverse("hosts:create"),
            data=json.dumps({"hostname": "x", "ip_address": "10.0.0.9"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(HostIP.objects.filter(hostname="x").exists())

    def test_update_denied_without_change_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.post(
            reverse("hosts:update", args=[self.host.id]),
            data=json.dumps({"hostname": "hacked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.host.refresh_from_db()
        self.assertEqual(self.host.hostname, "web01")

    def test_delete_denied_without_delete_permission(self):
        self.client.force_login(self._make_user("noperm"))
        response = self.client.post(reverse("hosts:delete", args=[self.host.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(HostIP.objects.filter(id=self.host.id).exists())

    def test_change_permission_does_not_grant_delete(self):
        # Permissions are per-action: holding one does not imply another.
        self.client.force_login(self._make_user("editor", "change_hostip"))
        response = self.client.post(reverse("hosts:delete", args=[self.host.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(HostIP.objects.filter(id=self.host.id).exists())

    # ---- allowed: user holding the matching permission -----------------

    def test_create_allowed_with_add_permission(self):
        self.client.force_login(self._make_user("creator", "add_hostip"))
        response = self.client.post(
            reverse("hosts:create"),
            data=json.dumps({"hostname": "new", "ip_address": "10.0.0.8"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(HostIP.objects.filter(hostname="new").exists())

    def test_update_allowed_with_change_permission(self):
        self.client.force_login(self._make_user("editor2", "change_hostip"))
        response = self.client.post(
            reverse("hosts:update", args=[self.host.id]),
            data=json.dumps({"hostname": "renamed"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.host.refresh_from_db()
        self.assertEqual(self.host.hostname, "renamed")

    def test_delete_allowed_with_delete_permission(self):
        self.client.force_login(self._make_user("remover", "delete_hostip"))
        response = self.client.post(reverse("hosts:delete", args=[self.host.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HostIP.objects.filter(id=self.host.id).exists())
