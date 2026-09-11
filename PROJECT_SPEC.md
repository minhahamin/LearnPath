# 프로젝트 빌드 프롬프트: 개인 학습 콘텐츠 큐레이터 (ReAct 기반)

아래 내용을 그대로 Claude Code(또는 다른 AI 코딩 에이전트)에게 프로젝트 루트에서 붙여넣어 시작하세요. 필요하면 섹션별로 나눠서 단계적으로 지시해도 됩니다.

---

## 0. 한 줄 요약

관심 키워드를 입력하면, ReAct(Thought→Action→Observation) 루프로 웹을 검색·평가하며 난이도별 학습 로드맵을 자동 생성해주는 개인 학습 큐레이터를 만든다. 백엔드는 Python(FastAPI), 프론트엔드는 React. 10 영업일(2주 평일) 내 완성이 목표다.

---

## 1. 프로젝트 목표 및 범위

**목표**: 사용자가 "배우고 싶은 주제"를 입력하면, 에이전트가 웹검색을 반복(ReAct)하며 자료를 찾고, 각 자료를 난이도(입문/중급/고급)와 신뢰도로 평가한 뒤, 순서가 있는 학습 로드맵(JSON)으로 정리해 React 화면에 보여준다.

**MVP 범위 (10일 내 완성 기준)**
- 키워드 1개 입력 → 로드맵 1개 생성 (다중 주제 동시 처리는 제외)
- 웹검색 도구는 1개(예: Tavily API, SerpAPI, 또는 Bing/Google 커스텀 검색 API 중 택1 — 무료 티어 있는 것 우선)
- ReAct 루프는 최대 반복 횟수(예: 5회)로 제한, 타임아웃 처리 필수
- 결과는 JSON 스키마로 강제(출력 계약) + 검증 실패 시 재시도(최대 2회)
- 진행 과정(Thought/Action/Observation)을 프론트에서 실시간 또는 단계별로 볼 수 있게 노출 (에이전트가 "어떻게 생각했는지" 보여주는 게 이 프로젝트의 차별점)
- SQLite에 로드맵 결과와 실행 로그(재시도 횟수, 실패 케이스, 소요 시간) 저장
- 과거에 생성한 로드맵 목록 조회 기능

**범위에서 제외 (10일 내 무리이므로 스트레치 목표로만 남김)**
- 사용자 로그인/인증
- 다국어 지원
- 로드맵 진행률 추적(체크리스트 등) — 시간 남으면 추가
- LangFuse 등 별도 관측 도구 연동 — 시간 남으면 추가

---

## 2. 기술 스택

- **백엔드**: Python 3.11+, FastAPI, Pydantic(출력 계약 스키마 검증), httpx(비동기 웹검색 호출), PostgreSQL(SQLAlchemy + psycopg 또는 asyncpg, 마이그레이션은 Alembic 권장)
- **LLM 연동**: OpenAI/Anthropic API 중 택1 (function calling / tool use 지원 모델)
- **웹검색 도구**: Tavily API(에이전트용으로 설계돼 있어 추천) 또는 SerpAPI
- **프론트엔드**: React (Vite 기반 추천), fetch/axios로 백엔드 API 호출, 상태관리는 useState/useReducer 정도로 충분 (Redux 불필요)
- **배포/실행**: 로컬 실행 기준으로 우선 완성, 시간 남으면 Docker Compose로 백엔드+프론트 묶기

---

## 3. 아키텍처

```
[React 프론트엔드]
   │  POST /api/curate { topic: string }
   ▼
[FastAPI 백엔드]
   │
   ├─ ReAct 루프 컨트롤러
   │    ├─ Thought: "다음에 뭘 검색할까?" (LLM 호출)
   │    ├─ Action: web_search(query) 도구 호출
   │    ├─ Observation: 검색 결과 요약 + 관련성/난이도 평가 (LLM 호출)
   │    └─ 반복 (최대 N회) → 충분한 자료 확보 시 종료
   │
   ├─ 출력 계약 검증기 (Pydantic 모델로 최종 로드맵 JSON 검증)
   ├─ 재시도 로직 (검증 실패 시 LLM에 에러 피드백 포함해 재요청, 최대 2회)
   └─ PostgreSQL 저장 (roadmaps 테이블, react_steps 테이블, run_logs 테이블)

   ▼
GET /api/roadmaps/{id}       → 완성된 로드맵 조회
GET /api/roadmaps/{id}/steps → 해당 로드맵의 ReAct 진행 단계 조회
GET /api/roadmaps            → 과거 로드맵 목록
```

---

## 4. 출력 계약 (Output Contract) — 최종 로드맵 JSON 스키마

Pydantic 모델로 아래 구조를 강제한다. LLM이 이 스키마를 벗어나면 검증 실패로 간주하고 재시도한다.

```json
{
  "topic": "string",
  "summary": "string (이 주제를 왜 이 순서로 배워야 하는지 2~3문장)",
  "levels": [
    {
      "level": "beginner | intermediate | advanced",
      "resources": [
        {
          "title": "string",
          "url": "string (http/https, 검색 결과에서 실제로 나온 URL만 허용)",
          "reason": "string (왜 이 자료가 이 단계에 적합한지)",
          "confidence": "high | medium | low"
        }
      ]
    }
  ],
  "total_estimated_hours": "number"
}
```

**검증 규칙 (필수)**
- `levels`는 beginner/intermediate/advanced 3개를 모두 포함해야 함
- 각 level의 `resources`는 최소 1개 이상
- `url`은 실제로 웹검색 Observation에서 나온 URL 목록에 포함된 것만 허용 (LLM이 URL을 지어내는 hallucination 방지 — 이게 이 프로젝트의 핵심 검증 포인트)
- `confidence`가 "low"인 자료는 3개 이상 포함되지 않도록 제한

---

## 5. ReAct 루프 상세 설계

1. **Thought**: 지금까지 모은 자료를 보고 "다음에 어떤 검색어로 무엇을 더 찾아야 하는지" LLM이 판단 (예: "입문 자료는 충분한데 고급 자료가 부족하다 → 'topic advanced tutorial' 검색 필요")
2. **Action**: 위 판단에 따라 `web_search(query: str)` 도구 호출
3. **Observation**: 검색 결과(제목, URL, 스니펫)를 LLM에게 주고 "이 결과가 어느 난이도에 해당하는지, 신뢰할 만한지" 평가시켜 구조화된 형태로 저장
4. 종료 조건: (a) 3단계 난이도 모두 자료가 충분히 모였거나 (b) 반복 횟수가 최대치(5회)에 도달하면 종료 → 최종 로드맵 생성 단계로 전환
5. 각 단계(Thought/Action/Observation)는 `react_steps` 테이블에 순서대로 저장해서 프론트에서 "에이전트가 어떻게 생각의 흐름을 거쳤는지" 재생할 수 있게 한다

---

## 6. 검증 & 재시도 파이프라인

- 1차 생성 후 Pydantic 검증
- 실패 시: 실패 사유(어떤 필드가 왜 틀렸는지)를 LLM에게 그대로 피드백으로 주고 재생성 요청
- 최대 2회 재시도, 그래도 실패하면 에러 상태로 저장하고 사용자에게 "일부 자료만 확인됨" 같은 부분 결과라도 반환
- 모든 시도(성공/실패, 소요 시간, 재시도 횟수)는 `run_logs` 테이블에 기록 → 나중에 "재시도율", "평균 소요 시간" 같은 간단한 통계를 뽑을 수 있게

---

## 7. 데이터베이스 스키마 (PostgreSQL)

```sql
CREATE TABLE roadmaps (
  id SERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  result_json JSONB NOT NULL,
  status TEXT NOT NULL, -- 'success' | 'partial' | 'failed'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE react_steps (
  id SERIAL PRIMARY KEY,
  roadmap_id INTEGER REFERENCES roadmaps(id) ON DELETE CASCADE,
  step_order INTEGER NOT NULL,
  step_type TEXT NOT NULL, -- 'thought' | 'action' | 'observation'
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE run_logs (
  id SERIAL PRIMARY KEY,
  roadmap_id INTEGER REFERENCES roadmaps(id) ON DELETE CASCADE,
  retry_count INTEGER DEFAULT 0,
  duration_ms INTEGER,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

`result_json`을 `JSONB`로 두면 나중에 SQL로 로드맵 내용을 직접 쿼리(예: 특정 난이도 자료만 필터링)할 때 편합니다. 로컬 개발은 Docker로 PostgreSQL 컨테이너 하나 띄우고(`docker run -e POSTGRES_PASSWORD=... -p 5432:5432 postgres:16`), SQLAlchemy 모델 + Alembic으로 마이그레이션 관리하는 걸 추천합니다.

---

## 8. API 명세

- `POST /api/curate` — body: `{ "topic": "string" }` → 응답: `{ "roadmap_id": int }` (비동기 처리 후 폴링 또는 SSE로 진행 상황 전달 — 시간 여유 있으면 SSE, 없으면 간단히 폴링 방식으로)
- `GET /api/roadmaps/{id}` — 완성된 로드맵 JSON + status
- `GET /api/roadmaps/{id}/steps` — ReAct 단계별 로그 (프론트에서 타임라인 UI로 표시)
- `GET /api/roadmaps` — 과거 로드맵 목록 (topic, status, created_at)

---

## 9. 프론트엔드(React) 요구사항

- **입력 화면**: 주제 입력창 + "큐레이션 시작" 버튼
- **진행 화면**: ReAct 단계를 타임라인 형태로 표시 (Thought는 회색, Action은 파란색, Observation은 초록색 등으로 구분) — 이게 이 프로젝트의 시각적 하이라이트이므로 신경 써서 구현
- **결과 화면**: level별(입문/중급/고급) 섹션으로 자료 카드 나열 (제목, 링크, 추천 이유, 신뢰도 배지)
- **히스토리 화면**: 과거 생성한 로드맵 목록, 클릭 시 결과 화면으로 이동
- 상태관리는 가볍게: React Query(TanStack Query) 사용 추천 (폴링/캐싱 편리), 없으면 useEffect + useState로도 충분

---

## 10. 10 영업일 일정 (평일 기준)

| Day | 작업 |
|---|---|
| 1 | 요구사항 확정, API 키 발급(LLM, 웹검색), FastAPI/React 프로젝트 스캐폴딩, Docker로 PostgreSQL 컨테이너 실행 + Alembic 마이그레이션으로 DB 스키마 생성 |
| 2 | 웹검색 도구 연동 함수 작성 + 단독 테스트 (mock 없이 실제 API 호출 확인) |
| 3 | ReAct 루프 핵심 로직 구현 (Thought/Action/Observation 1회전) |
| 4 | ReAct 루프 반복/종료 조건 완성 + react_steps 저장 로직 |
| 5 | 출력 계약(Pydantic 스키마) 정의 + 최종 로드맵 생성 로직 |
| 6 | 검증 실패 시 재시도 파이프라인 구현 + run_logs 기록 |
| 7 | FastAPI 엔드포인트 4개 완성 + Postman/curl로 통합 테스트 |
| 8 | React 입력/결과 화면 구현 + API 연동 |
| 9 | React 진행 화면(ReAct 타임라인 시각화) + 히스토리 화면 구현 |
| 10 | 통합 테스트, 예외 처리(검색 실패, LLM 타임아웃 등), README 작성, 데모 시나리오 준비 |

---

## 11. 예외 처리 체크리스트 (놓치기 쉬운 부분)

- 웹검색 API가 결과 0건을 반환할 때
- LLM이 스키마에 안 맞는 JSON을 계속 반환해서 재시도 한도를 초과할 때 → 부분 결과라도 사용자에게 보여주기
- 웹검색 API rate limit 도달 시 처리
- 동일 주제로 중복 요청 시 캐싱할지 여부 (선택사항)
- LLM이 존재하지 않는 URL을 만들어내는 경우 → §4의 URL 검증 규칙으로 반드시 차단

---

## 12. 데모 시나리오 (발표용)

1. "리액트 훅(React Hooks)" 같은 구체적인 주제 입력
2. 진행 화면에서 ReAct 단계가 실시간으로 쌓이는 것을 보여줌 ("에이전트가 이렇게 생각하고 검색했다")
3. 결과 로드맵에서 난이도별 자료와 추천 이유 확인
4. (있다면) 검증 실패 → 재시도 → 성공한 케이스를 run_logs에서 보여주며 "출력 계약과 재시도 전략이 실제로 hallucination을 걸러냈다"는 걸 강조 — 이 프로젝트의 핵심 셀링포인트

---

## 13. 환경변수/시크릿 템플릿 (.env.example)

AI에게 시크릿 관리 방식을 명시하지 않으면 키를 코드에 하드코딩하거나 제각각 이름으로 만들 수 있다. 아래를 그대로 `.env.example`로 만들어두고 실제 값이 든 `.env`는 `.gitignore`에 반드시 포함시킨다.

```
# LLM
OPENAI_API_KEY=
# 또는 ANTHROPIC_API_KEY=

# 웹검색 도구
TAVILY_API_KEY=

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://curator:curator@localhost:5432/curator_db

# 앱 설정
MAX_REACT_ITERATIONS=5
MAX_RETRY_COUNT=2
REQUEST_TIMEOUT_SECONDS=30

# 프론트엔드 (frontend/.env)
VITE_API_BASE_URL=http://localhost:8000
```

---

## 14. LLM Tool-Calling(Function Calling) 스키마 예시

ReAct의 Action 단계에서 LLM이 호출할 도구를 아래처럼 명확한 JSON schema로 정의해서 넘긴다. 이 스키마를 안 주면 AI가 라이브러리/모델별로 제각각 구현해서 나중에 프롬프트와 실제 함수 시그니처가 어긋나는 문제가 생긴다.

```json
{
  "name": "web_search",
  "description": "주어진 검색어로 웹을 검색해 제목, URL, 스니펫 목록을 반환한다. 학습 자료(튜토리얼, 문서, 아티클)를 찾을 때 사용한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "검색어. 예: 'React Hooks tutorial for beginners'"
      },
      "target_level": {
        "type": "string",
        "enum": ["beginner", "intermediate", "advanced"],
        "description": "이 검색이 어떤 난이도 자료를 채우기 위한 것인지"
      }
    },
    "required": ["query", "target_level"]
  }
}
```

- 이 스키마와 실제 파이썬 함수(`def web_search(query: str, target_level: str) -> list[SearchResult]`)의 인자 이름/타입을 반드시 일치시킬 것
- Observation 단계에서 LLM에게 돌려줄 응답 포맷도 고정(title, url, snippet 리스트)해서 AI가 매번 다른 구조로 파싱하지 않게 한다

---

## 15. 프로젝트 폴더 구조

AI에게 아래 트리 구조를 먼저 제시하면 파일을 산발적으로 만들지 않고 일관되게 작업한다.

```
learning-curator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트, CORS 설정
│   │   ├── api/
│   │   │   └── routes.py        # /api/curate, /api/roadmaps 등
│   │   ├── agent/
│   │   │   ├── react_loop.py    # ReAct 컨트롤러
│   │   │   ├── tools.py         # web_search 등 도구 정의
│   │   │   └── prompts.py       # Thought/Observation용 시스템 프롬프트
│   │   ├── schemas/
│   │   │   └── roadmap.py       # Pydantic 출력 계약 모델
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy 모델
│   │   │   └── session.py
│   │   └── core/
│   │       └── config.py        # .env 로드
│   ├── alembic/                 # 마이그레이션
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── InputPage.jsx
│   │   │   ├── ProgressPage.jsx   # ReAct 타임라인
│   │   │   ├── ResultPage.jsx
│   │   │   └── HistoryPage.jsx
│   │   ├── components/
│   │   └── api/
│   │       └── client.js
│   ├── package.json
│   └── .env.example
├── docker-compose.yml            # postgres + (선택)backend/frontend
├── PROJECT_SPEC.md               # 이 문서
└── README.md
```

---

## 16. CORS 설정

React(기본 `localhost:5173`, Vite 기준)와 FastAPI(`localhost:8000`)가 로컬에서 통신하려면 CORS 미들웨어가 필요하다. 빠뜨리기 쉬우니 초기 세팅 단계에 명시해서 포함시킨다.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 17. 토큰/비용 가드

ReAct 루프가 예상보다 많이 돌거나 무한루프에 빠지지 않도록 최대 반복 횟수 외에 아래 안전장치를 반드시 포함시킨다.

- `MAX_REACT_ITERATIONS`(기본 5) 도달 시 강제 종료 후 지금까지 모은 자료로 로드맵 생성
- 1회 전체 실행(큐레이션 1건)당 LLM 호출 총 토큰 수 상한 설정(예: 50,000 토큰) 후 초과 시 즉시 종료
- `REQUEST_TIMEOUT_SECONDS`(기본 30초)로 웹검색/LLM 호출 각각에 타임아웃 적용
- 모든 LLM 호출의 입출력 토큰 수를 `run_logs`에 누적 기록해서 나중에 "이번 실행에 비용이 얼마 들었는지" 확인 가능하게

---

## 18. Git 커밋 규칙

AI에게 작업을 시킬 때 "단계가 끝날 때마다 커밋해줘"라고 명시하면 문제가 생겼을 때 되돌리기 쉽다.

- 저장소 초기화 후 `.gitignore`에 `.env`, `__pycache__/`, `node_modules/`, `*.db` 포함
- 일정표(섹션 10)의 Day 단위 혹은 기능 단위로 커밋 (예: `feat: web_search 도구 구현`, `feat: ReAct 루프 반복/종료 조건`, `feat: 출력 계약 검증 + 재시도`)
- 커밋 전 실행 테스트(간단한 curl 또는 스크립트)를 통과했는지 확인 후 커밋

---

## 19. 로딩/에러 상태 UI 명세

프론트엔드에 "어떤 상태를 어떻게 보여줄지" 명시하지 않으면 단순 스피너만 나오는 경우가 많다. 아래 상태를 최소한 구분해서 구현한다.

| 상태 | 화면 표시 |
|---|---|
| 큐레이션 시작 직후 | "검색 계획을 세우는 중..." (Thought 단계) |
| 웹검색 중 | "'{query}' 검색 중..." (Action 단계, 실제 검색어 노출) |
| 결과 평가 중 | "자료를 평가하는 중..." (Observation 단계) |
| 검증 실패 → 재시도 중 | "일부 자료의 근거가 부족해 다시 확인하는 중... (재시도 {n}/2)" |
| 최대 반복/재시도 초과 | "일부 자료만 확인되었습니다" + 부분 결과 표시 |
| 완전 실패 | 에러 메시지 + "다시 시도" 버튼 |
| 완료 | 결과 화면으로 자동 전환 |

---

## 20. AI에게 실제로 시킬 때 사용법 (중요)

이 문서를 한 번에 통째로 주고 "다 만들어줘"라고 하지 말 것. 아래 순서로 나눠서 단계마다 결과를 확인하고 다음으로 넘어간다.

1. **1차 프롬프트**: 섹션 2(기술 스택), 15(폴더 구조), 13(.env), 16(CORS)를 주고 "프로젝트 스캐폴딩 + PostgreSQL 연결까지만 해줘"라고 요청 → 실행해서 서버가 뜨는지, DB 연결이 되는지 확인
2. **2차 프롬프트**: 섹션 14(도구 스키마)를 주고 "web_search 도구 함수만 구현하고 단독으로 테스트하는 스크립트도 같이 만들어줘" → 실제 API 키로 호출해서 결과 확인
3. **3차 프롬프트**: 섹션 5(ReAct 루프 설계)를 주고 "ReAct 루프 1회전만 먼저 구현해줘, 아직 반복/종료 조건은 넣지 마" → Thought/Action/Observation이 순서대로 잘 도는지 로그로 확인
4. **4차 프롬프트**: "이제 반복과 종료 조건(섹션 5의 종료 조건)을 추가해줘" → 최대 5회 제한이 실제로 걸리는지 확인
5. **5차 프롬프트**: 섹션 4(출력 계약)와 6(검증/재시도)을 주고 "최종 로드맵 생성 + 검증 + 재시도까지 구현해줘" → 일부러 이상한 주제를 넣어서 재시도가 실제로 도는지 확인
6. **6차 프롬프트**: 섹션 8(API 명세)을 주고 "엔드포인트 4개를 완성해줘" → curl/Postman으로 각각 테스트
7. **7차 프롬프트**: 섹션 9(프론트 요구사항)와 19(로딩/에러 UI)를 주고 화면별로 나눠서 요청 (입력 화면 → 진행 화면 → 결과 화면 → 히스토리 화면 순)
8. **마지막**: 섹션 11(예외 처리 체크리스트)을 주고 "이 목록에 있는 예외 상황들이 다 처리되는지 점검하고 빠진 부분 채워줘"

매 단계 끝날 때 섹션 18의 커밋 규칙대로 커밋해두면, 특정 단계에서 AI가 이상하게 코드를 바꿔도 그 지점으로 쉽게 되돌릴 수 있다.

---

이 문서를 프로젝트 루트에 `PROJECT_SPEC.md`로 저장해두고, 위 섹션 20의 순서대로 AI 코딩 에이전트에게 단계적으로 요청하면 진행 상황을 놓치지 않고 작업할 수 있습니다.