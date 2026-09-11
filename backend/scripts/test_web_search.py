"""Standalone smoke test for the web_search tool. Hits the real Tavily API.

Usage (from backend/):
    python scripts/test_web_search.py "React Hooks tutorial for beginners"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.tools import web_search  # noqa: E402


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "React Hooks tutorial for beginners"
    target_level = sys.argv[2] if len(sys.argv) > 2 else "beginner"

    print(f"query={query!r} target_level={target_level!r}")
    results = await web_search(query, target_level)

    if not results:
        print("No results returned. Check TAVILY_API_KEY in backend/.env.")
        return

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r.title}\n{r.url}\n{r.snippet[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
