# Railway 배포 가이드

이 저장소는 `backend/`와 `frontend/`를 **각각 별도의 Railway 서비스**로 배포하도록 준비되어 있습니다
(`backend/railway.json`, `frontend/railway.json`). Postgres는 Railway의 매니지드 플러그인을 씁니다.

로그인/결제 정보 입력은 Railway 계정 소유자만 할 수 있어서(OAuth, 카드 등록) 아래 1~2단계는
직접 진행해주셔야 합니다. 그 이후 서비스 생성·환경변수 설정·배포는 CLI로 같이 진행할 수 있습니다.

## 1. Railway CLI 로그인 (직접 진행)

```bash
railway login
```

브라우저가 열리며 인증합니다. 완료되면 `railway whoami`로 확인하세요.

## 2. 프로젝트 생성 (직접 또는 대시보드에서)

```bash
railway init
```

또는 [railway.app](https://railway.app) 대시보드에서 "New Project" → "Deploy from GitHub repo"로
`minhahamin/LearnPath`를 선택해도 됩니다.

## 3. 서비스 3개 구성

| 서비스 | Root Directory | 비고 |
|---|---|---|
| `postgres` | - | Railway 플러그인 "Add PostgreSQL"로 추가, `DATABASE_URL`은 자동 주입됨 |
| `backend` | `backend` | `railway.json`이 마이그레이션 + uvicorn 기동을 자동 처리 |
| `frontend` | `frontend` | `railway.json`이 `npm run build` 후 `serve`로 정적 파일 서빙 |

대시보드에서 서비스별로 **Settings → Root Directory**를 `backend` / `frontend`로 지정하거나,
CLI로 `railway service create`를 반복해서 만들 수 있습니다.

## 4. 환경변수 (backend 서비스)

```
GEMINI_API_KEY=...
TAVILY_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
MAX_REACT_ITERATIONS=5
MAX_RETRY_COUNT=2
REQUEST_TIMEOUT_SECONDS=30
MAX_TOKENS_PER_RUN=50000
CORS_ORIGINS=https://<frontend 서비스의 Railway 도메인>
DATABASE_URL=${{Postgres.DATABASE_URL}}   # Railway 변수 참조 문법으로 postgres 서비스와 연결
```

> `DATABASE_URL`은 Railway가 `postgres://` 형식으로 주는데, 코드(`backend/app/core/config.py`)에서
> 자동으로 `postgresql+asyncpg://`로 변환하므로 그대로 연결해도 됩니다.

## 5. 환경변수 (frontend 서비스)

Vite 환경변수는 **빌드 타임**에 값이 박히므로, 빌드 전에 반드시 설정되어 있어야 합니다.

```
VITE_API_BASE_URL=https://<backend 서비스의 Railway 도메인>
```

## 6. 배포

각 서비스에서 "Generate Domain"으로 공개 URL을 받은 뒤, 4/5단계의 상호 참조 URL을 채우고
재배포하면 됩니다. CLI로는:

```bash
railway up            # 현재 디렉터리를 연결된 서비스로 배포
railway domain         # 도메인 생성/확인
railway variables set KEY=VALUE
```

## 7. 배포 후 확인

- backend: `https://<backend-domain>/health` → `{"status":"ok"}`
- frontend: `https://<frontend-domain>` 접속 후 주제 입력 → 정상 동작 확인
