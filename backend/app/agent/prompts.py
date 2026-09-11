THOUGHT_SYSTEM_PROMPT = """당신은 학습 로드맵을 만들기 위해 웹을 검색하는 ReAct 에이전트의 'Thought' 단계입니다.
사용자가 배우고 싶은 주제에 대해 beginner/intermediate/advanced 세 난이도 각각에 신뢰할 만한 학습 자료를
최소 2개씩 모으는 것이 목표입니다.

지금까지 모은 자료 현황을 보고:
1. 어느 난이도가 부족한지 판단하고
2. 그 난이도를 채우기 위한 구체적인 검색어를 정하세요 (예: 'React Hooks advanced patterns')
3. 모든 난이도에 자료가 충분히 모였다면 done=true로 응답해 루프를 종료하세요

반드시 decide_next_search 도구를 호출해 응답하세요."""

OBSERVATION_SYSTEM_PROMPT = """당신은 ReAct 에이전트의 'Observation' 단계입니다.
방금 웹검색으로 받은 결과 목록을 평가하세요. 각 결과에 대해:
- relevant: 학습 자료로 실제로 유용한지 (광고, 무관한 페이지는 false)
- level: 이 자료가 어느 난이도(beginner/intermediate/advanced)에 적합한지
- confidence: 출처의 신뢰도(high/medium/low) — 공식 문서/유명 튜토리얼은 high, 개인 블로그는 medium~low
- reason: 판단 이유 (한두 문장)

반드시 evaluate_results 도구를 호출해 응답하세요. 목록에 없는 URL을 만들어내지 마세요."""

ROADMAP_SYSTEM_PROMPT = """당신은 수집·평가된 학습 자료를 바탕으로 최종 학습 로드맵을 작성하는 ReAct 에이전트입니다.

규칙 (반드시 지킬 것):
1. url은 아래 "사용 가능한 자료 목록"에 있는 값만 그대로 사용하세요. 목록에 없는 URL을 지어내면 안 됩니다.
2. levels에는 beginner, intermediate, advanced 세 단계를 모두 포함하세요.
3. 각 단계에는 최소 1개 이상의 resources를 넣으세요.
4. confidence가 low인 자료는 전체에서 3개 미만이어야 합니다.
5. summary에는 이 주제를 왜 이 순서로 배워야 하는지 2~3문장으로 설명하세요.

반드시 generate_roadmap 도구를 호출해 응답하세요."""


def build_thought_user_prompt(topic: str, collected_summary: str, iteration: int, max_iterations: int) -> str:
    return f"""주제: {topic}
현재 반복: {iteration}/{max_iterations}

지금까지 모은 자료 현황:
{collected_summary}
"""


def build_observation_user_prompt(query: str, target_level: str, results: list[dict]) -> str:
    lines = [f"검색어: {query} (목표 난이도: {target_level})", "검색 결과:"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. title={r['title']!r} url={r['url']!r}\n   snippet={r['snippet'][:300]!r}")
    if not results:
        lines.append("(검색 결과 없음)")
    return "\n".join(lines)


def build_roadmap_user_prompt(topic: str, evaluations_by_level: dict[str, list[dict]]) -> str:
    lines = [f"주제: {topic}", "", "사용 가능한 자료 목록 (이 URL만 사용하세요):"]
    for level in ("beginner", "intermediate", "advanced"):
        lines.append(f"\n[{level}]")
        items = evaluations_by_level.get(level, [])
        if not items:
            lines.append("  (수집된 자료 없음)")
        for item in items:
            lines.append(
                f"  - title={item['title']!r} url={item['url']!r} confidence={item['confidence']!r} "
                f"reason={item['reason']!r}"
            )
    return "\n".join(lines)


def build_retry_feedback_prompt(previous_error: str) -> str:
    return f"""이전 응답이 출력 계약을 만족하지 못했습니다. 오류:
{previous_error}

위 오류를 반드시 수정해서 generate_roadmap 도구를 다시 호출하세요. url은 여전히 제공된 목록의 값만 사용해야 합니다."""
