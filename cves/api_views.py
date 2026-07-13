from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import CVEFilter
from .models import CVE
from .serializers import CVEDetailSerializer, CVEListSerializer


class CVEPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class CVEViewSet(ReadOnlyModelViewSet):
    """Public, read-only CVE query API backed by Django ORM querysets."""

    lookup_field = "cve_id"
    lookup_value_regex = r"CVE-\d{4}-\d+"
    permission_classes = [AllowAny]
    pagination_class = CVEPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CVEFilter
    search_fields = ["cve_id", "description", "cwe_ids", "source_identifier"]
    ordering_fields = [
        "cve_id",
        "published_at",
        "last_modified_at",
        "cvss_base_score",
        "cvss_base_severity",
    ]
    ordering = ["-published_at", "cve_id"]

    def get_queryset(self):
        queryset = CVE.objects.all()
        if self.action == "list":
            return queryset.defer("reference_urls")
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return CVEListSerializer
        return CVEDetailSerializer
