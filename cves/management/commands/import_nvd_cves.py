import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cves.models import CVE
from cves.services import NVDRequestError, fetch_nvd_page, nvd_cve_to_fields

UPSERT_FIELDS = (
    "source_identifier",
    "description",
    "published_at",
    "last_modified_at",
    "vuln_status",
    "cvss_version",
    "cvss_vector",
    "cvss_base_score",
    "cvss_base_severity",
    "cwe_ids",
    "reference_urls",
    "updated_at",
)


class Command(BaseCommand):
    help = "Import CVE records from NVD CVE API 2.0 using safe, batched ORM upserts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10_000,
            help="Maximum number of NVD records to fetch (default: 10000).",
        )
        parser.add_argument(
            "--start-index",
            type=int,
            default=0,
            help="Zero-based NVD result offset to start from (default: 0).",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=2_000,
            help="NVD page size from 1 to 2000 (default: 2000).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=6.0,
            help="Seconds to wait between NVD pages without an API key (default: 6).",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Retries for each failed NVD request (default: 3).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Per-request network timeout in seconds (default: 30).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        start_index = options["start_index"]
        page_size = options["page_size"]
        delay = options["delay"]
        retries = options["retries"]
        timeout = options["timeout"]

        if limit < 1:
            raise CommandError("--limit must be at least 1.")
        if start_index < 0:
            raise CommandError("--start-index cannot be negative.")
        if not 1 <= page_size <= 2_000:
            raise CommandError("--page-size must be between 1 and 2000.")
        if delay < 0:
            raise CommandError("--delay cannot be negative.")
        if retries < 0:
            raise CommandError("--retries cannot be negative.")
        if timeout < 1:
            raise CommandError("--timeout must be at least 1.")

        api_key = os.environ.get("NVD_API_KEY")
        fetched = created = updated = skipped = 0
        next_index = start_index

        while fetched < limit:
            requested_size = min(page_size, limit - fetched)
            response = self._fetch_with_retry(
                next_index,
                requested_size,
                api_key=api_key,
                timeout=timeout,
                retries=retries,
            )
            items = response.get("vulnerabilities")
            if not isinstance(items, list):
                raise CommandError(
                    "NVD response did not contain a vulnerabilities list."
                )
            if not items:
                self.stdout.write(
                    self.style.WARNING("NVD returned no more records before the limit.")
                )
                break

            records = []
            for item in items[:requested_size]:
                raw_cve = item.get("cve") if isinstance(item, dict) else None
                if not isinstance(raw_cve, dict):
                    skipped += 1
                    continue
                try:
                    records.append(nvd_cve_to_fields(raw_cve))
                except ValueError:
                    skipped += 1

            page_created, page_updated = self._upsert(records)
            created += page_created
            updated += page_updated
            fetched += len(items[:requested_size])
            next_index += len(items)

            self.stdout.write(
                f"Fetched {fetched}/{limit}; created {created}, "
                f"updated {updated}, skipped {skipped}."
            )

            if len(items) < requested_size or fetched >= limit:
                break
            time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"NVD import complete: fetched={fetched}, created={created}, "
                f"updated={updated}, skipped={skipped}."
            )
        )

    def _fetch_with_retry(
        self,
        start_index,
        page_size,
        *,
        api_key,
        timeout,
        retries,
    ):
        for attempt in range(retries + 1):
            try:
                return fetch_nvd_page(
                    start_index,
                    page_size,
                    api_key=api_key,
                    timeout=timeout,
                )
            except NVDRequestError as error:
                if attempt == retries:
                    raise CommandError(str(error)) from error

                wait_seconds = min(2**attempt, 30)
                self.stderr.write(
                    self.style.WARNING(
                        f"NVD request failed; retrying in {wait_seconds} seconds."
                    )
                )
                time.sleep(wait_seconds)

        raise CommandError("NVD request retries were exhausted.")

    @staticmethod
    def _upsert(records):
        unique_records = {record["cve_id"]: record for record in records}
        if not unique_records:
            return 0, 0

        cve_ids = list(unique_records)
        existing_ids = set(
            CVE.objects.filter(cve_id__in=cve_ids).values_list("cve_id", flat=True)
        )
        now = timezone.now()
        objects = [
            CVE(**record, created_at=now, updated_at=now)
            for record in unique_records.values()
        ]

        with transaction.atomic():
            CVE.objects.bulk_create(
                objects,
                batch_size=100,
                update_conflicts=True,
                update_fields=UPSERT_FIELDS,
                unique_fields=["cve_id"],
            )

        updated = len(existing_ids)
        created = len(objects) - updated
        return created, updated
