import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$")
CVSS_METRIC_KEYS = (
    "cvssMetricV40",
    "cvssMetricV31",
    "cvssMetricV30",
    "cvssMetricV2",
)
CVSS_SEVERITIES = {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class NVDRequestError(RuntimeError):
    """Raised when a request to the fixed NVD endpoint cannot be completed."""


def fetch_nvd_page(
    start_index,
    results_per_page,
    *,
    api_key=None,
    timeout=30,
):
    """Fetch one bounded page from NVD without accepting a caller-controlled URL."""

    query = urlencode(
        {
            "startIndex": start_index,
            "resultsPerPage": results_per_page,
        }
    )
    headers = {
        "Accept": "application/json",
        "User-Agent": "django-practice-cve-importer/1.0",
    }
    if api_key:
        headers["apiKey"] = api_key

    request = Request(f"{NVD_CVE_API_URL}?{query}", headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise NVDRequestError(
            f"NVD returned HTTP {error.code} for the CVE import request."
        ) from error
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NVDRequestError("Could not fetch a valid response from NVD.") from error


def parse_nvd_datetime(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _english_description(descriptions):
    for description in descriptions or []:
        if description.get("lang") == "en":
            return description.get("value", "")
    return ""


def _valid_http_url(value):
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _reference_urls(references):
    urls = []
    for reference in references or []:
        url = reference.get("url", "").strip()
        if _valid_http_url(url) and url not in urls:
            urls.append(url)
    return urls


def _cwe_ids(weaknesses):
    identifiers = []
    for weakness in weaknesses or []:
        for description in weakness.get("description", []):
            value = description.get("value", "").strip().upper()
            if value and value not in identifiers:
                identifiers.append(value)

    joined = ",".join(identifiers)
    return joined[:1000]


def _cvss_summary(metrics):
    for metric_key in CVSS_METRIC_KEYS:
        candidates = metrics.get(metric_key) or []
        if not candidates:
            continue

        metric = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("type") == "Primary"
            ),
            candidates[0],
        )
        data = metric.get("cvssData") or {}
        raw_score = data.get("baseScore")
        try:
            score = Decimal(str(raw_score)) if raw_score is not None else None
        except (InvalidOperation, ValueError):
            score = None

        if score is not None and not Decimal("0") <= score <= Decimal("10"):
            score = None

        severity = str(data.get("baseSeverity") or "").upper()
        if severity not in CVSS_SEVERITIES:
            severity = ""

        return {
            "cvss_version": str(data.get("version") or "")[:16],
            "cvss_vector": str(data.get("vectorString") or "")[:255],
            "cvss_base_score": score,
            "cvss_base_severity": severity,
        }

    return {
        "cvss_version": "",
        "cvss_vector": "",
        "cvss_base_score": None,
        "cvss_base_severity": "",
    }


def nvd_cve_to_fields(cve):
    """Convert a NVD CVE object into values accepted by the CVE ORM model."""

    cve_id = str(cve.get("id") or "").upper()
    if not NVD_CVE_ID_PATTERN.fullmatch(cve_id):
        raise ValueError("NVD item does not contain a valid CVE ID.")

    return {
        "cve_id": cve_id,
        "source_identifier": str(cve.get("sourceIdentifier") or "")[:255],
        "description": _english_description(cve.get("descriptions")),
        "published_at": parse_nvd_datetime(cve.get("published")),
        "last_modified_at": parse_nvd_datetime(cve.get("lastModified")),
        "vuln_status": str(cve.get("vulnStatus") or "")[:64],
        "cwe_ids": _cwe_ids(cve.get("weaknesses")),
        "reference_urls": _reference_urls(cve.get("references")),
        **_cvss_summary(cve.get("metrics") or {}),
    }
