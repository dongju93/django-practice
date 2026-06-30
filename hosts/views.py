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

    def post(self, request):
        # =================================================================
        # [백엔드 관점] DataTables 서버 사이드 페이징 — 이 뷰가 하는 일
        # =================================================================
        #
        # DataTables는 "전체 데이터를 한 번에 받아 브라우저에서 페이지를 나눈다"는
        # 클라이언트 사이드 페이징을 쓰지 않는다. serverSide: true이므로
        # 페이지를 바꿀 때마다 이 엔드포인트에 POST 요청을 다시 보내고,
        # 서버가 "지금 화면에 필요한 행만" 잘라서 JSON으로 돌려준다.
        #
        # 페이징에 직접 관여하는 파라미터는 딱 두 개다.
        #
        #   start  — 0부터 시작하는 행 오프셋. "검색·정렬이 끝난 결과 목록에서
        #             몇 번째 행부터 가져올지"를 뜻한다. SQL의 OFFSET과 같다.
        #   length — 이번에 가져올 행 개수. SQL의 LIMIT과 같다.
        #
        # 예) pageLength=25일 때:
        #   1페이지 → start=0,  length=25  →  QuerySet[0:25]   → OFFSET 0  LIMIT 25
        #   2페이지 → start=25, length=25  →  QuerySet[25:50]  → OFFSET 25 LIMIT 25
        #   3페이지 → start=50, length=25  →  QuerySet[50:75]  → OFFSET 50 LIMIT 25
        #
        # N번째 페이지(1부터)의 start 공식: start = (N - 1) × length
        #
        # 페이징 처리 순서(이 순서를 바꾸면 페이지마다 행 순서가 달라진다):
        #   1) 전체 QuerySet 확보
        #   2) recordsTotal 계산 — 검색 전 전체 수 (페이징과 무관, 정보 표시용)
        #   3) 검색 필터 적용
        #   4) recordsFiltered 계산 — 검색 후 전체 수 (페이지 버튼 개수 결정)
        #   5) 정렬 적용 — 페이지를 자르기 전에 정렬해야 모든 페이지의 순서가 일관됨
        #   6) [start : start + length] 슬라이스 — 현재 페이지 행만 DB에서 조회
        #   7) 슬라이스된 행만 data 배열에 넣어 응답
        #
        # 응답에서 페이징 UI가 참조하는 필드:
        #
        #   recordsTotal    — DB에 있는 전체 행 수. 검색어와 무관.
        #   recordsFiltered — 검색 조건을 통과한 전체 행 수. data 배열 길이와 다르다.
        #                     data는 "현재 페이지" 행만 담고, recordsFiltered는
        #                     "검색 결과 전체" 행 수다. DataTables는
        #                     ceil(recordsFiltered / length) 로 전체 페이지 수를 계산한다.
        #                     예) recordsFiltered=63, length=25 → 3페이지.
        #   data            — 이번 요청의 start~start+length 구간에 해당하는 행 배열.
        #                     마지막 페이지는 length보다 짧을 수 있다.
        #                     예) 63건, length=25, 3페이지 → data 길이는 13.
        #
        # draw는 페이징 자체와 무관하다. 비동기 요청 순서 번호로,
        # 늦게 도착한 이전 응답을 버리기 위해 요청값을 그대로 돌려준다.
        #
        # -----------------------------------------------------------------
        # DataTables 요청 규격 (페이징 외 파라미터):
        # - search[value]: 모든 검색 대상 열에 적용할 검색어
        # - order[0][column], order[0][dir]: 정렬할 열 번호와 asc/desc 방향
        #
        # 예를 들어 DataTables 검색 입력창에 "web"을 입력하면 브라우저가 다음과 같이 보낸다.
        #
        #   POST /hosts/data/
        #   Header: X-CSRFToken: <csrftoken 쿠키 값>
        #   Content-Type: application/x-www-form-urlencoded
        #   Body:
        #     draw=2&start=0&length=25
        #     &search[value]=web&search[regex]=false
        #     &order[0][column]=0&order[0][dir]=desc
        #
        # apiCall()의 JSON body와 다르다. DataTables는 폼 인코딩 본문으로 내며,
        # 파라미터 이름은 GET 때와 동일하다. URL에는 쿼리스트링이 붙지 않는다.
        # Django는 본문을 파싱해 request.POST QueryDict에 넣는다.
        # request.POST 값은 문자열이므로 draw/start/length/order column은 int로 변환하고,
        # 검색어와 정렬 방향은 문자열로 가져온다.
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 10))
        search_value = request.POST.get("search[value]", "").strip()
        order_column = int(request.POST.get("order[0][column]", 0))
        order_direction = request.POST.get("order[0][dir]", "desc")

        qs = HostIP.objects.all()

        # [페이징 2단계] recordsTotal — 검색 전 전체 수.
        # 페이지 버튼 수 계산에는 쓰이지 않지만, "전체 N개 항목" 정보 문구에 사용된다.
        total = qs.count()

        if search_value:
            qs = qs.filter(
                Q(hostname__icontains=search_value)
                | Q(ip_address__icontains=search_value)
                | Q(description__icontains=search_value)
            )

        # [페이징 4단계] recordsFiltered — 검색 후 전체 수.
        # len(data)가 아니다. 현재 페이지 행 수가 아니라 검색 결과 전체 행 수다.
        # 프론트엔드가 ceil(recordsFiltered / length)로 페이지 버튼 개수를 만든다.
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

        # [페이징 6단계] 슬라이스 — 여기서 실제 페이징이 일어난다.
        # Django QuerySet[start : start + length]는 SQL OFFSET/LIMIT으로 변환된다.
        # DB는 전체 결과를 메모리에 올리지 않고, 요청된 구간만 반환한다.
        page_qs = qs.order_by(order_field)[start : start + length]

        # [페이징 7단계] data — 슬라이스된 행만 직렬화한다.
        # recordsFiltered=100이어도 length=25이면 data는 최대 25개.
        # 모델 객체는 JSON으로 직렬화할 수 없으므로 dict로 변환한다.
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

        # [페이징 응답] draw는 요청값을 그대로 에코. recordsTotal/recordsFiltered는
        # 페이지 수 계산용, data는 tbody를 채울 현재 페이지 행 배열.
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
