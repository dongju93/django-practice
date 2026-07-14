/* cspell:ignore csrftoken */

/*
 * [09] Django CSRF 토큰 읽기
 * Django가 브라우저 쿠키에 저장한 "csrftoken=..." 항목을 세미콜론 단위로 찾는다.
 * 찾은 토큰은 DataTables 목록 조회·생성·수정·삭제 POST 요청의 X-CSRFToken 헤더에 포함되어,
 * 서버가 이 요청이 현재 사이트에서 보낸 정상 요청인지 확인할 수 있게 한다.
 * 토큰이 없으면 빈 문자열을 반환하며, 그 경우 Django의 CSRF 검증에서 POST 요청이 거부될 수 있다.
 */
function getCsrfToken() {
  const name = "csrftoken=";
  return document.cookie.split(";")
    .map(c => c.trim())
    .find(c => c.startsWith(name))
    ?.substring(name.length) ?? "";
}

/*
 * [10] 생성·수정·삭제에 공통으로 사용하는 AJAX 함수
 * 호출 측에서 전달한 JavaScript 객체 body를 JSON.stringify로 JSON 문자열로 바꾼다.
 * $.ajax는 url에 POST 요청을 보내고, Content-Type으로 JSON 본문임을 서버에 알린다.
 * dataType: "json"은 JSON 응답 본문을 JavaScript 객체로 변환한다.
 * 반환된 jqXHR을 호출 측에서 await하면 변환된 객체가 data 변수로 돌아간다.
 */
function apiCall(url, body) {
  return $.ajax({
    url,
    type: "POST",
    contentType: "application/json",
    dataType: "json",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    data: JSON.stringify(body),
  });
}

/*
 * [10-A] 현재 페이지의 행·열 선택 상태 저장소
 * selectableFields의 순서는 DataTables의 데이터 열 순서와 같다. Actions 열은
 * 원본 데이터 필드가 아니므로 포함하지 않는다.
 *
 * selectedRows는 선택한 행의 원본 객체를 id 기준으로 보관하고, selectedFields는
 * 선택한 열 이름만 보관한다. 첫 행을 선택할 때 선택된 열이 없으면 모든 데이터 열을
 * 자동 선택하고, 이후 행을 추가해도 사용자가 이미 고른 열은 바꾸지 않는다.
 * 실제 선택 셀은 "선택 행 × 선택 열"로 계산한다.
 * 페이지 이동 시에는 두 저장소를 모두 비워 이전 페이지 선택을 남기지 않는다.
 */
const selectableFields = [
  "id",
  "hostname",
  "ip_address",
  "description",
  "is_active",
  "created_at",
  "updated_at",
];
const selectedRows = new Map();
const selectedFields = new Set();

/*
 * [10-B] 행·열 선택 요약 갱신
 * 복사 대상 셀 수는 선택한 행 수와 열 수의 곱이다. 둘 중 하나라도 선택되지
 * 않았으면 빈 객체가 복사되지 않도록 복사 버튼을 비활성화한다.
 */
function updateSelectionSummary() {
  $("#selectionSummary").text(
    `${selectedRows.size} rows × ${selectedFields.size} columns selected`
  );
  $("#btnCopySelected").prop(
    "disabled",
    selectedRows.size === 0 || selectedFields.size === 0
  );
}

/*
 * [10-C] 현재 페이지의 행·열 교차 영역에 선택 상태 표현
 * 행과 열의 선택 상태를 독립적으로 확인하고, 둘 다 선택된 셀만 파란 배경과
 * 테두리로 표시한다. 제목 셀은 선택된 열 자체를 표시한다.
 */
function refreshVisibleSelection(api) {
  api.rows({ page: "current" }).every(function () {
    const rowData = this.data();
    const rowNode = this.node();
    const isRowSelected = selectedRows.has(rowData.id);

    if (isRowSelected) {
      selectedRows.set(rowData.id, rowData);
    }
    $(rowNode).toggleClass("row-selected", isRowSelected);

    $(rowNode).children("td").each((columnIndex, cell) => {
      const field = selectableFields[columnIndex];
      $(cell).toggleClass(
        "cell-selected",
        Boolean(field && isRowSelected && selectedFields.has(field))
      );
    });
  });

  selectableFields.forEach((field, columnIndex) => {
    const header = $(api.column(columnIndex).header());
    header.toggleClass("column-selected", selectedFields.has(field));
  });

  updateSelectionSummary();
}

/*
 * [10-D] 사용자에게 복사 결과 알림
 * 성공과 실패를 색상만으로 구분하지 않고 문장으로도 전달한다.
 * 새 선택 작업을 시작할 때는 빈 문자열을 전달해 이전 결과를 지운다.
 */
function setCopyStatus(message, isError = false) {
  $("#copyStatus")
    .text(message)
    .toggleClass("text-success", Boolean(message) && !isError)
    .toggleClass("text-danger", Boolean(message) && isError);
}

/*
 * [11] DataTables 초기화와 목록 데이터 호출
 * URLS.data는 HTML 템플릿의 인라인 스크립트에서 Django {% url %} 태그로 주입된다.
 */
const table = $("#hostTable").DataTable({
  serverSide: true,
  processing: true,
  ajax: {
    url: URLS.data,
    type: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  },

  /*
   * [12] 서버 데이터 필드와 화면 열의 연결
   */
  columns: [
    { data: "id", width: "40px" },
    { data: "hostname", render: DataTable.render.text() },
    { data: "ip_address", render: DataTable.render.text() },
    { data: "description", defaultContent: "—", render: DataTable.render.text() },
    {
      data: "is_active",
      render: v => v
        ? '<span class="badge badge-active">Active</span>'
        : '<span class="badge badge-inactive">Inactive</span>',
      width: "80px",
    },
    { data: "created_at", render: DataTable.render.text() },
    { data: "updated_at", render: DataTable.render.text() },
    {
      data: "id",
      orderable: false,
      /*
       * [13] 행별 Edit/Delete 버튼 생성
       */
      render: id =>
        `<div class="d-flex gap-2 justify-content-center">
           <button class="btn btn-sm btn-outline-primary btn-edit" data-id="${id}">Edit</button>
           <button class="btn btn-sm btn-outline-danger btn-delete" data-id="${id}">Delete</button>
         </div>`,
      width: "130px",
    },
  ],

  /*
   * [14] 페이징·정렬 초기값
   */
  order: [[0, "desc"]],
  pageLength: 25,
  lengthMenu: [10, 25, 50, 100],
  language: { processing: "Loading…" },

  /*
   * [14-A] DataTables가 tbody를 다시 그린 직후 행·열 선택 상태 표현
   */
  drawCallback() {
    refreshVisibleSelection(this.api());
  },
});

/*
 * 페이지 번호, Previous, Next 등으로 현재 페이지가 바뀌면 이전 페이지의
 * 행·열 선택과 복사 결과를 모두 초기화한다.
 */
table.on("page.dt", () => {
  selectedRows.clear();
  selectedFields.clear();
  setCopyStatus("");
  updateSelectionSummary();
});

/*
 * [14-B] 행의 가장 왼쪽 # 셀 클릭으로 행 선택
 */
$("#hostTable tbody").on("click", "td:first-child", function () {
  const rowData = table.row($(this).closest("tr")).data();

  if (selectedRows.has(rowData.id)) {
    selectedRows.delete(rowData.id);
  } else {
    selectedRows.set(rowData.id, rowData);
    if (selectedFields.size === 0) {
      selectableFields.forEach(field => selectedFields.add(field));
    }
  }

  setCopyStatus("");
  refreshVisibleSelection(table);
});

/*
 * [14-C] 제목 셀 클릭으로 열 선택
 */
function toggleCurrentPageColumn(columnIndex) {
  const field = selectableFields[columnIndex];

  if (selectedFields.has(field)) {
    selectedFields.delete(field);
  } else {
    selectedFields.add(field);
  }

  setCopyStatus("");
  refreshVisibleSelection(table);
}

const tableHead = document.querySelector("#hostTable thead");
$("#hostTable thead th")
  .slice(0, selectableFields.length)
  .attr("tabindex", "0")
  .attr("title", "Click to select this column");

/*
 * DataTables도 제목 셀 클릭을 정렬에 사용하므로 capture 단계에서 먼저 처리한다.
 */
tableHead.addEventListener("click", event => {
  const header = event.target.closest("th");
  const columnIndex = $(header).index();
  if (!selectableFields[columnIndex]) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  toggleCurrentPageColumn(columnIndex);
}, true);

tableHead.addEventListener("keydown", event => {
  const header = event.target.closest("th");
  const columnIndex = $(header).index();
  if (!selectableFields[columnIndex] || !["Enter", " "].includes(event.key)) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  if (event.key === "Enter") {
    toggleCurrentPageColumn(columnIndex);
  }
}, true);

tableHead.addEventListener("keyup", event => {
  const header = event.target.closest("th");
  const columnIndex = $(header).index();
  if (!selectableFields[columnIndex] || event.key !== " ") return;

  event.preventDefault();
  event.stopImmediatePropagation();
  toggleCurrentPageColumn(columnIndex);
}, true);

/*
 * [14-D] 모든 페이지의 선택 상태 초기화
 */
$("#btnClearSelection").on("click", () => {
  selectedRows.clear();
  selectedFields.clear();
  setCopyStatus("");
  refreshVisibleSelection(table);
});

/*
 * [14-E] Clipboard API를 사용할 수 없는 환경의 최소 대체 복사
 */
function copyTextFallback(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();

  try {
    if (!document.execCommand("copy")) {
      throw new Error("The browser rejected the copy command.");
    }
  } finally {
    textarea.remove();
  }
}

/*
 * [14-F] 선택된 셀을 JSON 배열로 변환하고 클립보드에 복사
 */
$("#btnCopySelected").on("click", async () => {
  const jsonRows = Array.from(selectedRows.values()).map(rowData => {
    const jsonObject = {};
    selectableFields.forEach(field => {
      if (selectedFields.has(field)) {
        jsonObject[field] = rowData[field] ?? null;
      }
    });
    return jsonObject;
  });
  const jsonText = JSON.stringify(jsonRows, null, 2);

  try {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(jsonText);
    } else {
      copyTextFallback(jsonText);
    }
    const cellCount = selectedRows.size * selectedFields.size;
    setCopyStatus(`${cellCount} selected cells copied as JSON.`);
  } catch (error) {
    setCopyStatus(`Copy failed: ${error.message}`, true);
  }
});

/*
 * [15] Bootstrap 모달 제어 객체 생성
 */
const hostModal   = new bootstrap.Modal("#hostModal");
const deleteModal = new bootstrap.Modal("#deleteModal");

/*
 * [16] 생성용 초기 상태로 입력 폼 정리
 */
function resetForm() {
  $("#editId").val("");
  $("#hostForm")[0].reset();
  $("#fIsActive").prop("checked", true);
  $("#formError").addClass("d-none").text("");
  $("#hostModalTitle").text("Add Host");
}

/*
 * [17] Add Host 버튼 처리
 */
$("#btnAddHost").on("click", () => {
  resetForm();
  hostModal.show();
});

/*
 * [18] Save 버튼: 입력값 수집과 최소 검증
 */
$("#btnSaveHost").on("click", async () => {
  const id       = $("#editId").val();
  const hostname = $("#fHostname").val().trim();
  const ip       = $("#fIpAddress").val().trim();

  if (!hostname || !ip) {
    $("#formError").removeClass("d-none").text("Hostname and IP Address are required.");
    return;
  }

  /*
   * [19] 서버에 전송할 JSON 데이터와 URL 결정
   */
  const payload = {
    hostname,
    ip_address: ip,
    description: $("#fDescription").val().trim(),
    is_active: $("#fIsActive").is(":checked"),
  };

  const url = id
    ? `${URLS.index}${id}/update/`
    : URLS.create;

  /*
   * [20] 생성·수정 요청 결과 처리
   */
  const data = await apiCall(url, payload);

  if (data.success) {
    if (id) {
      selectedRows.delete(Number(id));
      updateSelectionSummary();
    }
    hostModal.hide();
    table.ajax.reload();
  } else {
    $("#formError").removeClass("d-none").text(data.error ?? "An error occurred.");
  }
});

/*
 * [21] Edit 버튼: 선택한 호스트의 상세 데이터 조회
 */
$("#hostTable").on("click", ".btn-edit", async function () {
  const id = $(this).data("id");
  const data = await $.ajax({
    url: `${URLS.index}${id}/`,
    type: "GET",
    dataType: "json",
  });

  /*
   * [22] 조회한 상세 데이터를 수정 폼에 표현
   */
  resetForm();
  $("#editId").val(data.id);
  $("#fHostname").val(data.hostname);
  $("#fIpAddress").val(data.ip_address);
  $("#fDescription").val(data.description);
  $("#fIsActive").prop("checked", data.is_active);
  $("#hostModalTitle").text("Edit Host");
  hostModal.show();
});

/*
 * [23] 삭제 대기 대상 보관
 */
let pendingDeleteId = null;

/*
 * [24] Delete 버튼: 삭제 대상 확인 화면 구성
 */
$("#hostTable").on("click", ".btn-delete", function () {
  pendingDeleteId = $(this).data("id");
  const row = table.row($(this).closest("tr")).data();
  $("#deleteLabel").text(`${row.hostname} (${row.ip_address})`);
  deleteModal.show();
});

/*
 * [25] 삭제 확정과 목록 재호출
 */
$("#btnConfirmDelete").on("click", async () => {
  if (!pendingDeleteId) return;
  const data = await apiCall(
    `${URLS.index}${pendingDeleteId}/delete/`,
    {}
  );
  if (data.success) {
    selectedRows.delete(Number(pendingDeleteId));
    updateSelectionSummary();
    deleteModal.hide();
    table.ajax.reload();
  }
  pendingDeleteId = null;
});
