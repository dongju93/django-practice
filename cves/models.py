from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

cve_id_validator = RegexValidator(
    regex=r"^CVE-\d{4}-\d{4,}$",
    message="CVE ID must use the format CVE-YYYY-NNNN.",
)


class CVE(models.Model):
    """A normalized, queryable record imported from the NVD CVE API."""

    class Severity(models.TextChoices):
        NONE = "NONE", "None"
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    cve_id = models.CharField(
        max_length=32,
        unique=True,
        validators=[cve_id_validator],
        help_text="CVE-YYYY-NNNN format",
    )
    source_identifier = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_modified_at = models.DateTimeField(null=True, blank=True)
    vuln_status = models.CharField(max_length=64, blank=True)
    cvss_version = models.CharField(max_length=16, blank=True)
    cvss_vector = models.CharField(max_length=255, blank=True)
    cvss_base_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    cvss_base_severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        blank=True,
    )
    cwe_ids = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Comma-separated CWE identifiers, for example CWE-79,CWE-89.",
    )
    reference_urls = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "cve_id"]
        indexes = [
            models.Index(fields=["published_at"], name="cve_published_idx"),
            models.Index(fields=["last_modified_at"], name="cve_modified_idx"),
            models.Index(fields=["cvss_base_severity"], name="cve_severity_idx"),
            models.Index(fields=["vuln_status"], name="cve_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cvss_base_score__isnull=True)
                | Q(cvss_base_score__gte=0, cvss_base_score__lte=10),
                name="cve_cvss_score_range",
            )
        ]
        verbose_name = "CVE"
        verbose_name_plural = "CVEs"

    def __str__(self):
        return self.cve_id
