from datetime import datetime, timezone

from tavily import AsyncTavilyClient

from core.config import settings
from core.logging import get_logger
from tools.credibility import score_domain

logger = get_logger(__name__)


class SearchTool:
    def __init__(self) -> None:
        self._client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        language: str = "it",
    ) -> list[dict]:
        logger.info("search.start", query=query, max_results=max_results)
        try:
            response = await self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=False,
            )
            results = response.get("results", [])
            logger.info("search.done", query=query, result_count=len(results))
            sources = []
            for r in results:
                domain = _extract_domain(r.get("url", ""))
                tier, score, note = score_domain(domain)
                sources.append({
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "domain": domain,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "credibility_tier": tier,
                    "credibility_score": score,
                    "credibility_note": note,
                })
            return sources
        except Exception as exc:
            logger.error("search.error", query=query, error=str(exc))
            return []


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return ""
