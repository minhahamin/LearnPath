# Railway 배포

## 🌐 현재 배포된 URL

- 프론트엔드: https://frontend-production-c5ba.up.railway.app
- 백엔드: https://backend-production-f989.up.railway.app (`/health`로 상태 확인)

Railway 프로젝트 `learning-curator`에 `backend` / `frontend` / `Postgres` 3개 서비스로 배포되어 있습니다.

---

이 저장소는 `backend/`와 `frontend/`를 **각각 별도의 Railway 서비스**로 배포하도록 준비되어 있습니다
(`backend/railpack.json`, `frontend/railpack.json` — Railway의 현재 기본 빌더인 **Railpack**이 읽는
설정 파일입니다. 예전 이름인 `railway.json`은 Railpack에서는 읽히지 않습니다). Postgres는 Railway의
매니지드 플러그인을 씁니다.

로그인/결제 정보 입력은 Railway 계정 소유자만 할 수 있어서(OAuth, 카드 등록) 1단계는 직접
진행해야 합니다. 그 이후 프로젝트/서비스 생성, 환경변수 설정, 배포는 Railway CLI로 재현할 수 있습니다
(아래 명령은 이번에 실제로 실행해 배포를 완료한 순서 그대로입니다).

## 1. Railway CLI 로그인 (직접 진행)

```bash
railway login
```

브라우저가 열리며 인증합니다. 완료되면 `railway whoami`로 확인하세요.

## 2. 프로젝트 생성

```bash
railway init --name learning-curator
```

## 3. Postgres + 서비스 2개 생성

```bash
railway add --database postgres
railway add --service backend
railway add --service frontend
```

## 4. backend 환경변수

```bash
railway variable set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --service backend --skip-deploys
railway variable set 'GEMINI_API_KEY=...' --service backend --skip-deploys
railway variable set 'TAVILY_API_KEY=...' --service backend --skip-deploys
railway variable set 'GEMINI_MODEL=gemini-2.5-flash' --service backend --skip-deploys
railway variable set 'MAX_REACT_ITERATIONS=5' --service backend --skip-deploys
railway variable set 'MAX_RETRY_COUNT=2' --service backend --skip-deploys
railway variable set 'REQUEST_TIMEOUT_SECONDS=30' --service backend --skip-deploys
railway variable set 'MAX_TOKENS_PER_RUN=50000' --service backend --skip-deploys
```

> `DATABASE_URL`은 Railway가 `postgres://` 형식으로 주는데, 코드(`backend/app/core/config.py`의
> `use_asyncpg_driver` validator)에서 자동으로 `postgresql+asyncpg://`로 바꾸므로 그대로 연결해도 됩니다.
> `${{Postgres.DATABASE_URL}}`은 Railway의 서비스 간 변수 참조 문법 — 쉘에서 `$`가 먼저 해석되지
> 않도록 반드시 작은따옴표로 감싸야 합니다.

## 5. 배포 + 도메인

```bash
railway up backend --path-as-root --service backend --detach
railway domain --service backend      # → https://backend-production-xxxx.up.railway.app
```

## 6. frontend 환경변수 + 배포

Vite 환경변수는 **빌드 타임**에 값이 박히므로, 빌드 전에 반드시 설정되어 있어야 합니다.

```bash
railway variable set 'VITE_API_BASE_URL=https://<backend 도메인>' --service frontend --skip-deploys
railway up frontend --path-as-root --service frontend --detach
railway domain --service frontend     # → https://frontend-production-xxxx.up.railway.app
```

## 7. CORS 연결 (backend)

```bash
railway variable set 'CORS_ORIGINS=https://<frontend 도메인>' --service backend
```

`--skip-deploys`를 빼면 변수 설정과 동시에 재배포까지 트리거됩니다.

## 8. 확인

- `curl https://<backend 도메인>/health` → `{"status":"ok"}`
- 브라우저로 프론트엔드 접속 → 개발자도구 네트워크 탭에서 `/api/roadmaps` 요청이 200으로
  오는지 확인 (CORS가 막히면 여기서 실패함)

## 겪었던 문제

- **`railway.json`이 무시됨**: Railway의 현재 기본 빌더는 Nixpacks가 아니라 **Railpack**이고,
  설정 파일 이름이 `railpack.json`으로 바뀌었습니다(`https://schema.railpack.com`). `railway.json`을
  써뒀더니 "No start command detected"로 빌드가 실패했고, 파일명을 바꾸자 바로 해결됐습니다.
- **`pip install -r requirements.txt`가 Railway에서만 실패**: 로컬 venv는 이미 설치돼 있던
  `pydantic`을 나중에 `google-genai`가 조용히 업그레이드해준 상태라 문제를 못 느꼈지만,
  Railway는 매번 클린 환경에서 `requirements.txt`를 그대로 설치하기 때문에 `pydantic==2.10.4`
  고정 버전이 `google-genai`가 요구하는 `pydantic>=2.12.5`와 충돌해 즉시 실패했습니다.
  로컬에서 실제로 동작 중인 버전(`2.13.5`)으로 핀을 맞추고, 배포 전 항상 **새 가상환경에서
  클린 설치가 되는지** 확인하는 습관으로 잡았습니다.
