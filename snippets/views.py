from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt  # CSRF 보호 비활성화
from rest_framework.parsers import JSONParser

from snippets.models import Snippet
from snippets.serializers import SnippetSerializer


@csrf_exempt
def snippet_list(request):
    """
    모든 코드 스니펫을 나열하거나 새 스니펫을 만듭니다.
    """
    match request.method:  # noqa
        case "GET":
            snippets = Snippet.objects.all()  # pylint: disable=no-member
            serializer = SnippetSerializer(snippets, many=True)
            # 리스트를 JSON으로 반환 시 safe=False 필요
            return JsonResponse(serializer.data, safe=False)
        case "POST":
            # 요청 본문(JSON)을 파싱
            data = JSONParser().parse(request)
            serializer = SnippetSerializer(data=data)
            if serializer.is_valid():
                serializer.save()  # 새 스니펫 저장 (내부적으로 create() 호출)
                return JsonResponse(serializer.data, status=201)
            return JsonResponse(serializer.errors, status=400)
        case _:
            return HttpResponse(status=405)


@csrf_exempt
def snippet_detail(request, pk):
    """
    코드 스니펫을 검색, 업데이트 또는 삭제합니다.
    """
    try:
        snippet = Snippet.objects.get(pk=pk)  # pylint: disable=no-member
    except Snippet.DoesNotExist:  # pylint: disable=no-member
        return HttpResponse(status=404)

    match request.method:  # noqa
        case "GET":
            serializer = SnippetSerializer(snippet)
            return JsonResponse(serializer.data)
        case "PUT":
            data = JSONParser().parse(request)
            # 기존 인스턴스와 함께 데이터 전달, update() 메서드 사용
            serializer = SnippetSerializer(snippet, data=data)
            if serializer.is_valid():
                # 스니펫 업데이트 (내부적으로 update() 호출)
                serializer.save()
                return JsonResponse(serializer.data)
            return JsonResponse(serializer.errors, status=400)
        case "DELETE":
            snippet.delete()
            return HttpResponse(status=204)
        case _:
            return HttpResponse(status=405)
