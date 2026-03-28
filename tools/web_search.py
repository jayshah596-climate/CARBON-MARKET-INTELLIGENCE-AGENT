"""
Web search tool for fetching real-time carbon market data.

Priority:
  1. Tavily API (if TAVILY_API_KEY is set) — high quality, structured results
  2. DuckDuckGo HTML scraping via requests + BeautifulSoup4 — free fallback
"""

from __future__ import annotations
import logging
from typing import Any

import requests
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude tool definition (passed to the Anthropic API)
# ---------------------------------------------------------------------------

WEB_SEARCH_TOOL_DEFINITION: dict[str, Any] = {
    "name": "search_web",
    "description": (
        "Search the web for real-time carbon market prices, ESG news, and policy "
        "updates. Use this to fetch current EUA, UKA, CCA, RGGI, VCM prices and "
        "any relevant carbon market regulatory developments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search query string, e.g. "
                    "'EU ETS EUA carbon price today EUR per tonne CO2'"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-10). Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


# ---------------------------------------------------------------------------
# Search implementations
# ---------------------------------------------------------------------------

def _search_tavily(query: str, max_results: int) -> str:
    """Use Tavily API for high-quality web search."""
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
        )
        parts: list[str] = []
        if response.get("answer"):
            parts.append(f"Summary: {response['answer']}\n")
        for result in response.get("results", []):
            parts.append(
                f"Source: {result.get('url', 'unknown')}\n"
                f"Title: {result.get('title', '')}\n"
                f"Content: {result.get('content', '')}\n"
            )
        return "\n---\n".join(parts) if parts else "No results found."
    except Exception as exc:
        logger.warning("Tavily search failed: %s — falling back to DuckDuckGo", exc)
        return _search_duckduckgo(query, max_results)


def _search_duckduckgo(query: str, max_results: int) -> str:
    """Scrape DuckDuckGo HTML search results as a fallback."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(
            url,
            data={"q": query},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        results: list[str] = []
        for result in soup.select(".result")[:max_results]:
            title_tag = result.select_one(".result__title")
            snippet_tag = result.select_one(".result__snippet")
            url_tag = result.select_one(".result__url")
            title = title_tag.get_text(strip=True) if title_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            link = url_tag.get_text(strip=True) if url_tag else ""
            if title or snippet:
                results.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}")
        return "\n---\n".join(results) if results else "No results found."
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return f"Search failed: {exc}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web for carbon market information.

    Uses Tavily if TAVILY_API_KEY is configured, otherwise DuckDuckGo HTML.

    Returns a formatted string with search results.
    """
    max_results = max(1, min(max_results, 10))
    logger.info("Searching web: %r (max_results=%d)", query, max_results)

    if settings.TAVILY_API_KEY:
        return _search_tavily(query, max_results)
    return _search_duckduckgo(query, max_results)
