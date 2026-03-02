import pytest
from unittest.mock import AsyncMock, patch

from tools.search import SearchTool, _extract_domain


def test_extract_domain():
    assert _extract_domain("https://www.bbc.com/news/article") == "www.bbc.com"
    assert _extract_domain("http://example.org/path?q=1") == "example.org"
    assert _extract_domain("not-a-url") == ""


@pytest.mark.asyncio
async def test_search_returns_formatted_results():
    mock_response = {
        "results": [
            {
                "url": "https://example.com/article",
                "title": "Test Article",
                "content": "Some content snippet.",
            }
        ]
    }

    with patch("tools.search.AsyncTavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search = AsyncMock(return_value=mock_response)

        tool = SearchTool()
        results = await tool.search("test query")

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/article"
    assert results[0]["title"] == "Test Article"
    assert results[0]["domain"] == "example.com"


@pytest.mark.asyncio
async def test_search_handles_error_gracefully():
    with patch("tools.search.AsyncTavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search = AsyncMock(side_effect=Exception("API error"))

        tool = SearchTool()
        results = await tool.search("test query")

    assert results == []
