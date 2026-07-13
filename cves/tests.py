from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .filters import CVEFilter
from .forms import CVEForm
from .models import CVE


class CVEFixtureMixin:
    def create_cve(self, **overrides):
        values = {
            "cve_id": "CVE-2026-10001",
            "description": "A critical example vulnerability",
            "published_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "last_modified_at": datetime(2026, 7, 2, tzinfo=timezone.utc),
            "vuln_status": "Analyzed",
            "cvss_version": "3.1",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "cvss_base_score": Decimal("9.8"),
            "cvss_base_severity": CVE.Severity.CRITICAL,
            "cwe_ids": "CWE-79,CWE-89",
            "reference_urls": ["https://example.com/advisory"],
        }
        values.update(overrides)
        return CVE.objects.create(**values)


class CVEFormTests(TestCase):
    def test_form_normalizes_cve_and_reference_values(self):
        form = CVEForm(
            data={
                "cve_id": "cve-2026-12345",
                "description": "Stored through the form",
                "cvss_base_score": "7.5",
                "cvss_base_severity": "HIGH",
                "cwe_ids": "cwe-79\nCWE-89, CWE-79",
                "reference_urls": (
                    "https://example.com/one\nhttps://example.com/two\n"
                    "https://example.com/one"
                ),
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        cve = form.save()
        self.assertEqual(cve.cve_id, "CVE-2026-12345")
        self.assertEqual(cve.cwe_ids, "CWE-79,CWE-89")
        self.assertEqual(
            cve.reference_urls,
            ["https://example.com/one", "https://example.com/two"],
        )

    def test_form_rejects_non_http_reference_url(self):
        form = CVEForm(
            data={
                "cve_id": "CVE-2026-12346",
                "reference_urls": "javascript:alert(1)",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("reference_urls", form.errors)


class CVEFilterAndAPITests(CVEFixtureMixin, TestCase):
    def setUp(self):
        self.critical = self.create_cve()
        self.low = self.create_cve(
            cve_id="CVE-2026-10002",
            description="A low severity example",
            cvss_base_score=Decimal("2.1"),
            cvss_base_severity=CVE.Severity.LOW,
            cwe_ids="CWE-200",
        )

    def test_filter_uses_orm_for_keyword_severity_and_score(self):
        filterset = CVEFilter(
            {"q": "critical", "severity": "CRITICAL", "score_min": "9"},
            queryset=CVE.objects.all(),
        )

        self.assertTrue(filterset.form.is_valid(), filterset.form.errors)
        self.assertEqual(list(filterset.qs), [self.critical])

    def test_public_api_filters_results_with_django_filter(self):
        response = self.client.get(
            reverse("cve-list"),
            {"severity": "CRITICAL", "score_min": "9", "page_size": 100},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["cve_id"], self.critical.cve_id)
        self.assertNotIn("reference_urls", payload["results"][0])

    def test_public_api_detail_exposes_reference_urls(self):
        response = self.client.get(
            reverse("cve-detail", kwargs={"cve_id": self.critical.cve_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["reference_urls"], self.critical.reference_urls
        )

    def test_public_api_is_read_only(self):
        response = self.client.post(
            reverse("cve-list"), {}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 405)


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    }
)
class CVECRUDViewTests(CVEFixtureMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="editor", password="safe-password"
        )
        permissions = Permission.objects.filter(
            content_type__app_label="cves",
            codename__in=["add_cve", "change_cve", "delete_cve"],
        )
        self.user.user_permissions.add(*permissions)
        self.client.force_login(self.user)

    def test_authorized_user_can_create_update_and_delete_a_cve(self):
        create_response = self.client.post(
            reverse("cves:create"),
            {
                "cve_id": "CVE-2026-20001",
                "description": "Created through the HTML CRUD form",
                "cvss_base_score": "8.1",
                "cvss_base_severity": "HIGH",
                "cwe_ids": "CWE-79",
                "reference_urls": "https://example.com/cve-2026-20001",
            },
        )

        self.assertRedirects(
            create_response,
            reverse("cves:detail", kwargs={"cve_id": "CVE-2026-20001"}),
        )
        cve = CVE.objects.get(cve_id="CVE-2026-20001")

        update_response = self.client.post(
            reverse("cves:edit", kwargs={"cve_id": cve.cve_id}),
            {
                "cve_id": cve.cve_id,
                "description": "Updated through the HTML CRUD form",
                "cvss_base_score": "9.0",
                "cvss_base_severity": "CRITICAL",
                "cwe_ids": "CWE-89",
                "reference_urls": "https://example.com/updated",
            },
        )

        self.assertRedirects(
            update_response,
            reverse("cves:detail", kwargs={"cve_id": cve.cve_id}),
        )
        cve.refresh_from_db()
        self.assertEqual(cve.description, "Updated through the HTML CRUD form")
        self.assertEqual(cve.cvss_base_severity, CVE.Severity.CRITICAL)

        delete_response = self.client.post(
            reverse("cves:delete", kwargs={"cve_id": cve.cve_id})
        )

        self.assertRedirects(delete_response, reverse("cves:list"))
        self.assertFalse(CVE.objects.filter(pk=cve.pk).exists())

    def test_anonymous_user_is_redirected_before_a_mutation(self):
        self.client.logout()

        response = self.client.get(reverse("cves:create"))

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={reverse('cves:create')}",
        )


class NVDImportCommandTests(TestCase):
    @patch("cves.management.commands.import_nvd_cves.fetch_nvd_page")
    def test_command_imports_and_upserts_nvd_records(self, fetch_page):
        fetch_page.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2026-30001",
                        "sourceIdentifier": "security@example.com",
                        "published": "2026-07-01T00:00:00.000",
                        "lastModified": "2026-07-02T00:00:00.000",
                        "vulnStatus": "Analyzed",
                        "descriptions": [
                            {"lang": "en", "value": "Imported CVE description"}
                        ],
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "type": "Primary",
                                    "cvssData": {
                                        "version": "3.1",
                                        "vectorString": "CVSS:3.1/AV:N",
                                        "baseScore": 9.8,
                                        "baseSeverity": "CRITICAL",
                                    },
                                }
                            ]
                        },
                        "weaknesses": [
                            {
                                "description": [
                                    {"lang": "en", "value": "CWE-79"},
                                ]
                            }
                        ],
                        "references": [
                            {"url": "https://example.com/advisory"},
                            {"url": "ftp://example.com/not-stored"},
                        ],
                    }
                }
            ]
        }

        call_command(
            "import_nvd_cves",
            limit=1,
            page_size=1,
            delay=0,
            verbosity=0,
        )

        cve = CVE.objects.get(cve_id="CVE-2026-30001")
        self.assertEqual(cve.cvss_base_score, Decimal("9.8"))
        self.assertEqual(cve.cwe_ids, "CWE-79")
        self.assertEqual(cve.reference_urls, ["https://example.com/advisory"])

        fetch_page.return_value["vulnerabilities"][0]["cve"]["descriptions"][0][
            "value"
        ] = "Updated imported description"
        call_command(
            "import_nvd_cves",
            limit=1,
            page_size=1,
            delay=0,
            verbosity=0,
        )

        self.assertEqual(CVE.objects.count(), 1)
        cve.refresh_from_db()
        self.assertEqual(cve.description, "Updated imported description")
