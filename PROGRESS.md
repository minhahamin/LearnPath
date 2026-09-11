# 진행 상황

`learning_curator_project_prompt.md` 스펙 기준 빌드 로그. 완료 항목은 체크, 진행 중/예정은 미체크로 표시.

## 0. 스캐폴딩
- [x] 폴더 구조 생성 (`backend/app/{api,agent,schemas,db,core}`, `backend/alembic`, `backend/scripts`, `frontend/src/{pages,components,api}`)

## 1. 백엔드 기반
- [x] `core/config.py` — .env 설정 로더
- [x] `db/models.py`, `db/session.py` — SQLAlchemy 모델/세션
- [ ] `alembic` 마이그레이션 (roadmaps / react_steps / run_logs)
- [x] `requirements.txt`, `.env.example`

## 2. 웹검색 도구
- [x] `agent/tools.py` — Tavily `web_search()`
- [x] `scripts/test_web_search.py` — 단독 테스트 스크립트 (실제 키 필요, 미실행)

## 3~4. ReAct 루프
- [x] `agent/prompts.py` — Thought/Observation/Roadmap 프롬프트
- [x] `agent/react_loop.py` — Thought→Action→Observation 반복 + 반복/종료 조건 (Gemini function calling으로 구조화 출력)

## 5~6. 출력 계약 & 재시도
- [x] `schemas/roadmap.py` — Pydantic 출력 계약 (URL 화이트리스트 검증 포함)
- [x] 검증 실패 시 재시도 로직 + `run_logs` 기록 (토큰 사용량 포함)

## 7~8. API
- [x] `api/routes.py` — `/api/curate`, `/api/roadmaps`, `/api/roadmaps/{id}`, `/api/roadmaps/{id}/steps`
- [x] `main.py` — FastAPI 앱 + CORS

## 9. 프론트엔드
- [x] Vite 프로젝트 스캐폴딩 (`package.json`, `vite.config.js`)
- [x] `InputPage` — 주제 입력
- [x] `ProgressPage` — ReAct 타임라인 (Thought 회색/Action 파랑/Observation 초록), 1.5s 폴링
- [x] `ResultPage` — 난이도별 자료 카드 + 신뢰도 배지
- [x] `HistoryPage` — 과거 로드맵 목록

## 10. 인프라 & 문서
- [x] `docker-compose.yml` — PostgreSQL 컨테이너 (포트 5434, 로컬 네이티브 Postgres와 충돌 회피)
- [x] `PROJECT_SPEC.md` (스펙 문서 사본)
- [x] `README.md` — 실행 방법
- [x] `.gitignore`, git init + 커밋

## 11. 검증
- [x] 백엔드 서버 기동 확인 (`uvicorn` 실행, `/health` `/api/roadmaps` `/api/curate` 응답 확인)
- [x] DB 마이그레이션 적용 확인 (`roadmaps`/`react_steps`/`run_logs` 테이블 생성됨)
- [x] API 키 없이 `/api/curate` 호출 시 실패가 graceful하게 `run_logs`/status='failed'로 기록되는지 확인
- [x] 프론트엔드 dev 서버 기동 확인 (`npm run dev`, 브라우저로 InputPage/ProgressPage/HistoryPage/ResultPage 렌더링 직접 확인)
- [x] **실제 키로 end-to-end 라이브 테스트 완료** — "React Hooks" 주제로 브라우저에서 직접 실행:
  ReAct 3회전(beginner→intermediate→advanced 순서로 검색) → 1차 시도에 출력 계약 통과(재시도 0회) →
  9개 실제 자료(입문/중급/고급 각 3개)로 로드맵 완성. 소요 29.5초, 총 8,724 토큰. 결과는
  `roadmaps` 테이블 id=1에 그대로 남겨둠(진짜 데이터라 테스트 후 삭제하지 않음).

### 변경 로그
- LLM을 Anthropic Claude → **Google Gemini**(`gemini-2.5-flash`, function calling)로 교체. 실제 발급받은 키로
  라이브 테스트 완료 (`_call_tool`의 `tool_config.mode="ANY"` 강제 호출 방식, `parameters`는 기존 JSON-schema
  스타일 dict를 그대로 재사용 가능함을 확인). `thinking_config(thinking_budget=0)`으로 불필요한 사고 토큰 차단.
- Gemini가 간헐적으로 `503 UNAVAILABLE`(모델 과부하)을 반환해 `_call_tool`에 지수 백오프 재시도
  (`google.genai.errors.ServerError`, 최대 3회, 1s/2s)를 추가함.
- 프론트엔드 파비콘 추가 (`frontend/index.html`, 나침반 이모지 SVG data URI).
- `README.md`를 포트폴리오용으로 재작성 (스크린샷 3장 `docs/screenshots/`, Mermaid 시퀀스 다이어그램,
  기술적 의사결정 하이라이트, 트러블슈팅 노트 포함). 스크린샷은 실제 라이브 실행 화면을 캡처한 것.
  Gemini 무료 키가 `gemini-2.5-flash` 기준 **일 20회** 제한임을 라이브 429 에러로 확인함.
- 사용자 요청으로 전체 UI를 카카오톡 파스텔/픽셀 테마로 재테마링 (`frontend/src/index.css` 전면 개편,
  Google Fonts `Jua`/`Gaegu`/`Press Start 2P`, 픽셀 별·구름 배경, 도트 테두리, 말풍선 스타일 타임라인,
  칩/뱃지에 이모지 아이콘 추가). `docs/screenshots/`의 README 스크린샷 3장도 새 테마로 재캡처.
- GitHub(`git@github.com:minhahamin/LearnPath.git`)의 `main`에 push 완료 (git init부터 진행, 비밀키
  미포함 확인 후 커밋).
- **Railway에 실제 배포 완료** — `backend`/`frontend`/`Postgres` 3개 서비스, CLI로 프로젝트 생성부터
  도메인 발급·CORS 연결까지 전부 진행. 라이브 URL은 `docs/DEPLOY.md` 상단 및 README 참고.
  배포 중 겪은 문제(Railway 기본 빌더가 Railpack이라 `railway.json`이 아니라 `railpack.json`을
  읽어야 함, `requirements.txt`의 `pydantic` 핀이 `google-genai`와 충돌해 클린 설치 실패)와 해결
  과정은 `docs/DEPLOY.md` 하단 "겪었던 문제" 참고.

### 트러블슈팅 메모
- 로컬 Postgres(native, 포트 5432)가 이미 떠 있어서 Docker의 `0.0.0.0:5432` 포워딩과 충돌 — `127.0.0.1` 연결이 조용히 로컬 인스턴스로 가서 인증 오류처럼 보였음. `docker-compose.yml`에서 포트를 **5434**로 변경해 해결. (`DATABASE_URL`도 5434로 맞춰둠)
