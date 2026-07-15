# django-practice

Django와 Django REST Framework 연습용 프로젝트입니다. 앱은 연습 목적에 따라 자유롭게 추가·삭제될 수 있습니다.

| 스택          | 버전 / 비고                                                     |
| ------------- | --------------------------------------------------------------- |
| Python        | `>=3.12` (`.python-version`: 3.12)                              |
| Django        | 5.2.x                                                           |
| DRF           | 3.17.x                                                          |
| 패키지 관리   | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| DB            | SQLite (`db.sqlite3`)                                           |
| 정적 파일     | WhiteNoise                                                      |
| 프로덕션 서버 | uWSGI (`uwsgi.ini`)                                             |

학습 참고:

1. [Django 튜토리얼](https://docs.djangoproject.com/en/5.2/intro/tutorial01/)
2. [Django REST Framework 튜토리얼](https://www.django-rest-framework.org/tutorial/1-serialization/)

---

## 사전 요구사항

1. **Python 3.12+**
2. **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — 의존성 설치·실행에 사용

```bash
# macOS (Homebrew 예시)
brew install uv
```

외부 DB(PostgreSQL 등)·Redis·Docker는 필수가 아닙니다. 개발 기본은 SQLite 한 파일입니다.

---

## 설치

저장소 루트에서:

```bash
# 의존성 설치 (런타임 + lockfile 기준)
uv sync

# 개발 도구(debug-toolbar, mypy, pylint, djlint 등)까지 포함
uv sync --group dev
```

가상환경은 uv가 `.venv`에 관리합니다. 이후 명령은 `uv run ...`으로 실행하는 것을 권장합니다.

---

## 환경 설정

설정 모듈은 환경별로 분리되어 있습니다.

| 용도 | 설정 모듈                   | 진입점                    | 설정 주입                   |
| ---- | --------------------------- | ------------------------- | --------------------------- |
| 개발 | `main.settings.development` | `manage.py`               | env 파일 없음 (코드 기본값) |
| 운영 | `main.settings.production`  | `main.wsgi` / `main.asgi` | `.env.production` 로드      |

### 개발

env 파일·추가 설정 없이 실행합니다. DEBUG일 때 `django-debug-toolbar`가 켜집니다.

### 운영

프로젝트 루트의 `.env.production`을 `main.settings.production`이 기동 시 로드합니다.  
git에 올리지 마세요(`.gitignore` 대상).

```bash
cp .env.production.example .env.production
# 값을 채운 뒤 uWSGI 등으로 실행
```

| 변수                                    | 필수                | 설명                                                   |
| --------------------------------------- | ------------------- | ------------------------------------------------------ |
| `DJANGO_SECRET_KEY`                     | ✅                  | 비어 있으면 안 됨                                      |
| `DJANGO_ALLOWED_HOSTS`                  | ✅                  | 예: `example.com,www.example.com`                      |
| `DJANGO_DEBUG`                          | 권장 `false`        | 기본 `false`                                           |
| `DJANGO_SESSION_COOKIE_SECURE`          | ✅                  | HTTPS 후 `true`                                        |
| `DJANGO_CSRF_COOKIE_SECURE`             | ✅                  | HTTPS 후 `true`                                        |
| `DJANGO_SECURE_SSL_REDIRECT`            | ✅                  | HTTPS 리다이렉트                                       |
| `DJANGO_SECURE_HSTS_SECONDS`            | ✅                  | HSTS 초 단위 (롤아웃 시 짧게 시작 가능)                |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | ✅                  | 서브도메인 HSTS                                        |
| `DJANGO_SECURE_HSTS_PRELOAD`            | ✅                  | HSTS preload                                           |
| `DJANGO_TRUST_X_FORWARDED_PROTO`        | 선택 (기본 `false`) | 신뢰 프록시가 `X-Forwarded-Proto`를 덮어쓸 때만 `true` |

boolean 값은 `true` / `false` / `1` / `0` / `yes` / `no` / `on` / `off` 만 허용됩니다.

---

## 실행 방법

### 1. DB 마이그레이션

```bash
uv run python manage.py migrate
```

### 2. (선택) 관리자 계정

```bash
uv run python manage.py createsuperuser
```

### 3. 개발 서버

```bash
uv run python manage.py runserver
# → http://127.0.0.1:8000/
```

다른 포트:

```bash
uv run python manage.py runserver 0.0.0.0:8080
```

### 4. 운영 (uWSGI)

`.env.production`을 준비한 뒤:

```bash
uv run python manage.py collectstatic --noinput
uv run python manage.py migrate
uv run uwsgi --ini uwsgi.ini
```

`uwsgi.ini`의 `static-map`은 uWSGI 매직 변수 `%d`(ini 파일이 있는 디렉터리)를 쓰므로 로컬 절대 경로를 넣지 않아도 됩니다. WhiteNoise도 미들웨어로 정적 파일을 서빙하므로, reverse proxy 뒤에서 static map 없이도 동작할 수 있습니다.

---

## 개발 도구 · 품질 검사

```bash
ruff format .
ruff check --fix .
uv run mypy .
uv run pylint .
uv run djlint . --reformat --profile=django
uv run python manage.py test
```

| 도구                 | 용도                                 |
| -------------------- | ------------------------------------ |
| ruff                 | 포맷·import 정렬 (`I`)               |
| mypy                 | 타입 검사 (django-stubs / drf-stubs) |
| pylint               | 정적 분석 (`pylint-django`)          |
| djlint               | Django 템플릿 포맷                   |
| django-debug-toolbar | 개발 시 SQL/요청 패널                |

타입·lint 도구는 `django_settings_module = main.settings.development` 를 기준으로 합니다.

---

## 설정 요약

- **타임존**: `Asia/Seoul`
- **DB**: SQLite (`BASE_DIR / db.sqlite3`)
- **정적 파일**: `STATIC_ROOT = static/`, WhiteNoise `CompressedManifestStaticFilesStorage`
- **의존성**: `pyproject.toml` / `uv.lock` 참고

---

## 빠른 시작

```bash
uv sync --group dev
uv run python manage.py migrate
uv run python manage.py createsuperuser   # 선택
uv run python manage.py runserver
```

브라우저: `http://127.0.0.1:8000/`
