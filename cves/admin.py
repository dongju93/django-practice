from django.contrib import admin

from .models import CVE


@admin.register(CVE)
class CVEAdmin(admin.ModelAdmin):
    list_display = (
        "cve_id",
        "cvss_base_severity",
        "cvss_base_score",
        "vuln_status",
        "published_at",
        "last_modified_at",
    )
    list_filter = ("cvss_base_severity", "vuln_status")
    search_fields = ("cve_id", "description", "cwe_ids", "source_identifier")
    ordering = ("-published_at", "cve_id")
    readonly_fields = ("created_at", "updated_at")
