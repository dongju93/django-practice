from rest_framework import permissions, viewsets

from snippets.models import Snippet
from snippets.serializers import SnippetSerializer


class SnippetViewSet(viewsets.ModelViewSet):
    """익명 사용자에게 읽기를, 모델 권한이 있는 사용자에게 CRUD를 제공합니다."""

    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]
