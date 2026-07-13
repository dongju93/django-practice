import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .models import CVE

cwe_id_pattern = re.compile(r"(?:CWE-\d+|NVD-CWE-(?:NOINFO|OTHER))\Z")
http_url_validator = URLValidator(schemes=["http", "https"])


class CVEForm(forms.ModelForm):
    """Validates manual CRUD input before it reaches the ORM."""

    cwe_ids = forms.CharField(
        required=False,
        label="CWE IDs",
        help_text="Comma- or line-separated CWE IDs (for example, CWE-79, CWE-89).",
    )
    reference_urls = forms.CharField(
        required=False,
        label="Reference URLs",
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="One HTTP(S) URL per line.",
    )
    cvss_base_score = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=10,
        decimal_places=1,
        max_digits=3,
    )
    published_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    last_modified_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = CVE
        fields = [
            "cve_id",
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
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.reference_urls:
            self.initial["reference_urls"] = "\n".join(self.instance.reference_urls)

    def clean_cve_id(self):
        return self.cleaned_data["cve_id"].upper()

    def clean_cwe_ids(self):
        raw_value = self.cleaned_data["cwe_ids"]
        cwe_ids = []
        for value in re.split(r"[,\n]+", raw_value):
            normalized = value.strip().upper()
            if not normalized:
                continue
            if not cwe_id_pattern.fullmatch(normalized):
                raise ValidationError(f"Invalid CWE identifier: {normalized}")
            if normalized not in cwe_ids:
                cwe_ids.append(normalized)
        return ",".join(cwe_ids)

    def clean_reference_urls(self):
        raw_value = self.cleaned_data["reference_urls"]
        urls = []
        for value in raw_value.splitlines():
            url = value.strip()
            if not url:
                continue
            http_url_validator(url)
            if url not in urls:
                urls.append(url)
        return urls
