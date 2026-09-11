import httpx
from pydantic import BaseModel

from app.core.config import get_settings

TAVILY_URL = "https://api.tavily.com/search"


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


WEB_SEARCH_TOOL_SCHEMA = {
    "name": "web_search",
    "description": (
        "주어진 검색어로 웹을 검색해 제목, URL, 스니펫 목록을 반환한다. "
        "학습 자료(튜토리얼, 문서, 아티클)를 찾을 때 사용한다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "검색어. 예: 'React Hooks tutorial for beginners'",
            },
            "target_level": {
                "type": "string",
                "enum": ["beginner", "intermediate", "advanced"],
                "description": "이 검색이 어떤 난이도 자료를 채우기 위한 것인지",
            },
        },
        "required": ["query", "target_level"],
    },
}


async def web_search(query: str, target_level: str) -> list[SearchResult]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            TAVILY_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": 5,
                "search_depth": "basic",
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
        )
        for item in data.get("results", [])
    ]
