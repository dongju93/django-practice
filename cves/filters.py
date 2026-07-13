from django import forms
from django.db.models import Q
from django_filters import (
    CharFilter,
    ChoiceFilter,
    DateFilter,
    FilterSet,
    NumberFilter,
)

from .models import CVE


class CVEFilter(FilterSet):
    """Shared, explicitly whitelisted filters for the HTML and REST listings."""

    q = CharFilter(method="filter_keyword", label="Keyword")
    cve_id = CharFilter(field_name="cve_id", lookup_expr="icontains", label="CVE ID")
    cwe_id = CharFilter(field_name="cwe_ids", lookup_expr="icontains", label="CWE ID")
    severity = ChoiceFilter(
        field_name="cvss_base_severity",
        choices=[("", "All severities"), *CVE.Severity.choices],
        label="Severity",
    )
    vuln_status = CharFilter(field_name="vuln_status", lookup_expr="iexact")
    score_min = NumberFilter(field_name="cvss_base_score", lookup_expr="gte")
    score_max = NumberFilter(field_name="cvss_base_score", lookup_expr="lte")
    published_after = DateFilter(
        field_name="published_at",
        lookup_expr="date__gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    published_before = DateFilter(
        field_name="published_at",
        lookup_expr="date__lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    modified_after = DateFilter(
        field_name="last_modified_at",
        lookup_expr="date__gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    modified_before = DateFilter(
        field_name="last_modified_at",
        lookup_expr="date__lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = CVE
        # Explicit filters are declared above; keep Meta.fields empty and typed
        # so mypy accepts the FilterSet Meta contract.
        fields: list[str] = []

    def filter_keyword(self, queryset, _name, value):
        keyword = value.strip()
        if not keyword:
            return queryset

        return queryset.filter(
            Q(cve_id__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(cwe_ids__icontains=keyword)
            | Q(source_identifier__icontains=keyword)
        )
