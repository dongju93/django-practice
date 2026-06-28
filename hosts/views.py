import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .models import HostIP


class HostIPListView(LoginRequiredMixin, View):
    """Renders the main page; DataTables fetches data via Ajax."""

    def get(self, request):
        return render(request, "hosts/index.html")


class HostIPDataView(LoginRequiredMixin, View):
    """Ajax endpoint consumed by DataTables (server-side processing)."""
    raise_exception = True  # return 403 instead of redirect — keeps Ajax responses as JSON

    def get(self, request):
        # DataTables 요청 규격:
        # - draw: 비동기 요청 순서 번호
        # - start: 검색 결과에서 이번 페이지가 시작할 0 기준 위치
        # - length: 이번 페이지에서 요청하는 행 개수
        # - search[value]: 모든 검색 대상 열에 적용할 검색어
        # - order[0][column], order[0][dir]: 정렬할 열 번호와 asc/desc 방향
        #
        # 예를 들어 DataTables 검색 입력창에 "web"을 입력하면 브라우저가 다음과 같은
        # GET 요청을 보낸다. 검색값은 JSON body가 아니라 URL 쿼리 파라미터에 들어온다.
        #
        # /hosts/data/?draw=2&start=0&length=25
        #     &search[value]=web&search[regex]=false
        #     &order[0][column]=0&order[0][dir]=desc
        #
        # 브라우저에서 search%5Bvalue%5D=web으로 보이더라도 Django가 URL 디코딩한 뒤
        # request.GET이라는 QueryDict에 {"search[value]": "web"} 형태로 제공한다.
        # request.GET 값은 문자열이므로 draw/start/length/order column은 int로 변환하고,
        # 검색어와 정렬 방향은 문자열로 가져온다.
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
        search_value = request.GET.get("search[value]", "").strip()
        order_column = int(request.GET.get("order[0][column]", 0))
        order_direction = request.GET.get("order[0][dir]", "desc")

        qs = HostIP.objects.all()

        # recordsTotal은 검색 조건을 적용하기 전의 전체 데이터 수다.
        # 검색 결과가 0개여도 DataTables가 원래 전체 규모를 표시할 수 있도록 별도로 계산한다.
        total = qs.count()

        if search_value:
            qs = qs.filter(
                Q(hostname__icontains=search_value)
                | Q(ip_address__icontains=search_value)
                | Q(description__icontains=search_value)
            )

        # recordsFiltered는 검색 조건을 적용한 뒤의 전체 결과 수다.
        # 현재 페이지의 data 개수가 아니라, 검색 조건에 맞는 모든 행의 개수다.
        # DataTables는 이 값을 length로 나눠 검색 결과의 전체 페이지 수를 계산한다.
        filtered = qs.count()

        # DataTables의 화면 열 번호를 실제 Django 모델 필드로 변환한다.
        # 정렬은 페이지를 자르기 전에 적용해야 모든 페이지의 행 순서가 일관된다.
        order_fields = (
            "id",
            "hostname",
            "ip_address",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "id",
        )
        order_field = order_fields[order_column] if 0 <= order_column < len(order_fields) else "id"
        if order_direction == "desc":
            order_field = f"-{order_field}"

        # 정렬된 검색 결과 중 현재 페이지에 필요한 구간만 DB에서 조회한다.
        # 예: start=25, length=25이면 QuerySet[25:50]이며 SQL의 OFFSET 25, LIMIT 25에 해당한다.
        page_qs = qs.order_by(order_field)[start : start + length]

        # data에는 현재 페이지 행만 넣는다. 모델 객체 자체는 JSON으로 직렬화할 수 없으므로,
        # DataTables columns 설정과 동일한 키를 가진 dict로 변환한다.
        data = [
            {
                "id": h.id,
                "hostname": h.hostname,
                "ip_address": h.ip_address,
                "description": h.description,
                "is_active": h.is_active,
                "created_at": h.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at": h.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
            for h in page_qs
        ]

        # 응답 JSON 규격 자체는 기존과 동일하다.
        # 이번 변경으로 달라진 것은 order 요청을 QuerySet에 반영한 뒤 data를 자른다는 처리 방식이다.
        #
        # draw: 요청에서 받은 번호를 그대로 반환해 늦게 도착한 과거 응답을 구분하게 한다.
        # recordsTotal: 검색 전 전체 수
        # recordsFiltered: 검색 후 전체 수
        # data: 검색·정렬·페이징까지 적용된 현재 페이지 행 배열
        return JsonResponse(
            {
                "draw": draw,
                "recordsTotal": total,
                "recordsFiltered": filtered,
                "data": data,
            }
        )


class HostIPCreateView(LoginRequiredMixin, View):
    raise_exception = True

    def post(self, request):
        try:
            body = json.loads(request.body)
            host = HostIP.objects.create(
                hostname=body["hostname"],
                ip_address=body["ip_address"],
                description=body.get("description", ""),
                is_active=body.get("is_active", True),
            )
            return JsonResponse({"success": True, "id": host.id}, status=201)
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


class HostIPDetailView(LoginRequiredMixin, View):
    raise_exception = True

    def get(self, request, pk):
        host = get_object_or_404(HostIP, pk=pk)
        return JsonResponse(
            {
                "id": host.id,
                "hostname": host.hostname,
                "ip_address": host.ip_address,
                "description": host.description,
                "is_active": host.is_active,
            }
        )


class HostIPUpdateView(LoginRequiredMixin, View):
    raise_exception = True

    def post(self, request, pk):
        host = get_object_or_404(HostIP, pk=pk)
        try:
            body = json.loads(request.body)
            host.hostname = body.get("hostname", host.hostname)
            host.ip_address = body.get("ip_address", host.ip_address)
            host.description = body.get("description", host.description)
            host.is_active = body.get("is_active", host.is_active)
            host.save()
            return JsonResponse({"success": True})
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


class HostIPDeleteView(LoginRequiredMixin, View):
    raise_exception = True

    def post(self, request, pk):
        host = get_object_or_404(HostIP, pk=pk)
        host.delete()
        return JsonResponse({"success": True})
