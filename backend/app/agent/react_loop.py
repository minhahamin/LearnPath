import asyncio
import logging
import time

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from app.agent.prompts import (
    OBSERVATION_SYSTEM_PROMPT,
    ROADMAP_SYSTEM_PROMPT,
    THOUGHT_SYSTEM_PROMPT,
    build_observation_user_prompt,
    build_retry_feedback_prompt,
    build_roadmap_user_prompt,
    build_thought_user_prompt,
)
from app.agent.tools import web_search
from app.core.config import get_settings
from app.db.models import ReactStep, Roadmap, RunLog
from app.db.session import AsyncSessionLocal
from app.schemas.roadmap import RoadmapContract

LEVELS = ("beginner", "intermediate", "advanced")
MIN_RESOURCES_PER_LEVEL = 2

DECIDE_TOOL = {
    "name": "decide_next_search",
    "description": "지금까지 모은 자료 상태를 보고 다음 검색어를 정하거나, 충분하면 종료를 선언한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string", "description": "현재 상태 판단과 다음 행동 이유"},
            "done": {"type": "boolean", "description": "모든 난이도에 자료가 충분히 모였으면 true"},
            "query": {"type": "string", "description": "done이 false일 때 사용할 검색어"},
            "target_level": {"type": "string", "enum": list(LEVELS)},
        },
        "required": ["reasoning", "done"],
    },
}

EVALUATE_TOOL = {
    "name": "evaluate_results",
    "description": "검색 결과 목록에서 각 항목의 관련성/난이도/신뢰도를 평가한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "evaluations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "relevant": {"type": "boolean"},
                        "level": {"type": "string", "enum": list(LEVELS)},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "reason": {"type": "string"},
                    },
                    "required": ["url", "title", "relevant", "level", "confidence", "reason"],
                },
            }
        },
        "required": ["evaluations"],
    },
}

ROADMAP_TOOL = {
    "name": "generate_roadmap",
    "description": "수집·평가된 학습 자료를 바탕으로 최종 학습 로드맵을 생성한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "summary": {"type": "string"},
            "levels": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": list(LEVELS)},
                        "resources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "reason": {"type": "string"},
                                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                                },
                                "required": ["title", "url", "reason", "confidence"],
                            },
                        },
                    },
                    "required": ["level", "resources"],
                },
            },
            "total_estimated_hours": {"type": "number"},
        },
        "required": ["topic", "summary", "levels", "total_estimated_hours"],
    },
}


class ReactRunner:
    def __init__(self, roadmap_id: int, topic: str):
        self.roadmap_id = roadmap_id
        self.topic = topic
        self.settings = get_settings()
        self.client = genai.Client(api_key=self.settings.gemini_api_key)
        self.collected: dict[str, list[dict]] = {lvl: [] for lvl in LEVELS}
        self._step_order = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    async def _persist_step(self, step_type: str, content: str, data: dict | list | None = None) -> None:
        self._step_order += 1
        async with AsyncSessionLocal() as session:
            session.add(
                ReactStep(
                    roadmap_id=self.roadmap_id,
                    step_order=self._step_order,
                    step_type=step_type,
                    content=content,
                    data=data,
                )
            )
            await session.commit()

    async def _call_tool(self, system: str, user_prompt: str, tool: dict, max_tokens: int = 1024) -> dict:
        function_declaration = types.FunctionDeclaration(
            name=tool["name"], description=tool["description"], parameters=tool["input_schema"]
        )
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            tools=[types.Tool(function_declarations=[function_declaration])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY", allowed_function_names=[tool["name"]]
                )
            ),
        )

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.settings.gemini_model, contents=user_prompt, config=config
                    ),
                    timeout=self.settings.request_timeout_seconds,
                )
                break
            except errors.ServerError:
                # transient 5xx (e.g. model overloaded) - backoff and retry
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(2**attempt)
            except errors.ClientError as exc:
                # 429 (rate limit) is transient and worth retrying with a longer
                # backoff; other 4xx (bad request, auth) will never succeed on retry.
                if exc.code != 429 or attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(10 * (attempt + 1))
            except TimeoutError:
                # asyncio.wait_for timeout - the request may have been transient
                # (network blip, momentarily overloaded model).
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(2**attempt)

        usage = response.usage_metadata
        if usage is not None:
            self.input_tokens += usage.prompt_token_count or 0
            self.output_tokens += (usage.total_token_count or 0) - (usage.prompt_token_count or 0)

        if not response.candidates:
            reason = getattr(response.prompt_feedback, "block_reason", None)
            raise RuntimeError(f"model returned no candidates for {tool['name']} (block_reason={reason})")

        for part in response.candidates[0].content.parts:
            if part.function_call:
                return dict(part.function_call.args)
        raise RuntimeError(f"model did not return a function_call for {tool['name']}")

    def _collected_summary(self) -> str:
        lines = []
        for level in LEVELS:
            lines.append(f"- {level}: {len(self.collected[level])}개")
        return "\n".join(lines)

    def _enough_collected(self) -> bool:
        return all(len(self.collected[lvl]) >= MIN_RESOURCES_PER_LEVEL for lvl in LEVELS)

    async def run_react_phase(self) -> None:
        max_iterations = self.settings.max_react_iterations
        for iteration in range(1, max_iterations + 1):
            if self.total_tokens >= self.settings.max_tokens_per_run:
                await self._persist_step("thought", "토큰 예산(max_tokens_per_run) 초과로 조기 종료합니다.")
                return

            try:
                decision = await self._call_tool(
                    THOUGHT_SYSTEM_PROMPT,
                    build_thought_user_prompt(self.topic, self._collected_summary(), iteration, max_iterations),
                    DECIDE_TOOL,
                )
            except Exception as exc:  # Gemini rate limit / timeout / auth error
                await self._persist_step("thought", f"다음 행동 결정 실패로 수집을 종료합니다: {exc}")
                return
            await self._persist_step("thought", decision.get("reasoning", ""))

            if decision.get("done") or self._enough_collected():
                return

            query = decision.get("query") or self.topic
            target_level = decision.get("target_level") or "beginner"
            await self._persist_step(
                "action", f"web_search(query={query!r}, target_level={target_level!r})"
            )

            try:
                results = await web_search(query, target_level)
            except Exception as exc:  # network / rate limit / auth errors
                await self._persist_step("observation", f"검색 실패: {exc}")
                continue

            if not results:
                await self._persist_step("observation", "검색 결과 0건.")
                continue

            try:
                evaluation = await self._call_tool(
                    OBSERVATION_SYSTEM_PROMPT,
                    build_observation_user_prompt(query, target_level, [r.model_dump() for r in results]),
                    EVALUATE_TOOL,
                )
            except Exception as exc:  # Gemini rate limit / timeout / auth error
                await self._persist_step("observation", f"평가 실패, 이번 검색 결과는 건너뜁니다: {exc}")
                continue
            evaluations = evaluation.get("evaluations", [])
            snippet_by_url = {r.url: r.snippet for r in results}
            for item in evaluations:
                item["snippet"] = snippet_by_url.get(item.get("url"), "")

            kept = 0
            for item in evaluations:
                if not item.get("relevant"):
                    continue
                level = item.get("level")
                if level not in self.collected:
                    continue
                self.collected[level].append(item)
                kept += 1
            await self._persist_step(
                "observation",
                f"{len(evaluations)}건 평가, {kept}건 관련성 있음으로 채택. 현재 수집 현황:\n{self._collected_summary()}",
                data={"query": query, "target_level": target_level, "evaluations": evaluations},
            )

        await self._persist_step(
            "thought", f"최대 반복 횟수({max_iterations}회)에 도달해 수집을 종료합니다."
        )

    async def generate_roadmap(self) -> tuple[dict | None, int, str | None]:
        """Returns (result_dict_or_None, retry_count, error_message)."""
        allowed_urls = {item["url"] for items in self.collected.values() for item in items}
        user_prompt = build_roadmap_user_prompt(self.topic, self.collected)

        last_error: str | None = None
        for attempt in range(self.settings.max_retry_count + 1):
            prompt = user_prompt if attempt == 0 else f"{user_prompt}\n\n{build_retry_feedback_prompt(last_error)}"
            await self._persist_step(
                "thought",
                f"최종 로드맵 생성 시도 {attempt + 1}/{self.settings.max_retry_count + 1}",
            )
            try:
                raw = await self._call_tool(ROADMAP_SYSTEM_PROMPT, prompt, ROADMAP_TOOL, max_tokens=2048)
                contract = RoadmapContract.model_validate(raw)
                contract.validate_urls_against_allowlist(allowed_urls)
                await self._persist_step("observation", "출력 계약 검증 통과.")
                return contract.model_dump(mode="json"), attempt, None
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)
                await self._persist_step("observation", f"출력 계약 검증 실패: {last_error}")
            except (errors.APIError, RuntimeError, TimeoutError) as exc:
                # Gemini rate limit / timeout / auth error / no function_call - treat
                # like a failed attempt so we fall back to a partial result instead
                # of aborting the whole run.
                last_error = str(exc)
                await self._persist_step("observation", f"로드맵 생성 요청 실패: {last_error}")

        return None, self.settings.max_retry_count, last_error


def _build_partial_result(topic: str, collected: dict[str, list[dict]]) -> dict:
    return {
        "topic": topic,
        "summary": "일부 난이도만 자료가 확인되어 부분 결과로 제공합니다.",
        "levels": [
            {
                "level": level,
                "resources": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "reason": item["reason"],
                        "confidence": item["confidence"],
                    }
                    for item in items
                ],
            }
            for level, items in collected.items()
            if items
        ],
        "total_estimated_hours": None,
    }


async def run_curation(roadmap_id: int, topic: str) -> None:
    start = time.monotonic()
    runner = ReactRunner(roadmap_id, topic)
    status = "failed"
    result: dict | None = None
    error_message: str | None = None
    retry_count = 0

    try:
        await runner.run_react_phase()
        has_any = any(runner.collected[lvl] for lvl in LEVELS)
        if not has_any:
            error_message = "검색 결과를 전혀 확보하지 못했습니다."
        else:
            result, retry_count, gen_error = await runner.generate_roadmap()
            if result is not None:
                status = "success"
            else:
                result = _build_partial_result(topic, runner.collected)
                status = "partial"
                error_message = gen_error
    except Exception as exc:  # unexpected failure (API auth, DB, etc.)
        logger.exception("run_curation failed for roadmap_id=%s topic=%r", roadmap_id, topic)
        error_message = str(exc)
        status = "failed"

    duration_ms = int((time.monotonic() - start) * 1000)

    async with AsyncSessionLocal() as session:
        roadmap = await session.get(Roadmap, roadmap_id)
        if roadmap is not None:
            roadmap.status = status
            roadmap.result_json = result
        session.add(
            RunLog(
                roadmap_id=roadmap_id,
                retry_count=retry_count,
                duration_ms=duration_ms,
                input_tokens=runner.input_tokens,
                output_tokens=runner.output_tokens,
                error_message=error_message,
            )
        )
        await session.commit()
