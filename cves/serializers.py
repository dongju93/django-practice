from rest_framework import serializers

from .models import CVE


class CVEListSerializer(serializers.ModelSerializer):
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
            "cvss_base_score",
            "cvss_base_severity",
            "cwe_ids",
        ]


class CVEDetailSerializer(CVEListSerializer):
    class Meta(CVEListSerializer.Meta):
        fields = [
            *CVEListSerializer.Meta.fields,
            "cvss_vector",
            "reference_urls",
            "created_at",
            "updated_at",
        ]
