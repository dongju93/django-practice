import re
from pathlib import Path

from django.contrib.auth import get_user_model
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
