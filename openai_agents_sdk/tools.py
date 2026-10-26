import json
from typing import Any
from urllib.parse import urlparse

from agents import RunContextWrapper, function_tool

from .context import ResearchContext


@function_tool
def search_web(ctx: RunContextWrapper[ResearchContext], query: str) -> str:
    """Search the web and return results whose URLs may be fetched this run."""
    if not query.strip():
        raise ValueError("Search query must not be empty.")

    from tools.web_search import web_search

    response = web_search(query)
    normalized_results: list[dict[str, Any]] = []
    for result in response.get("result", []):
        item = dict(result)
        url = item.get("url") or item.get("href")
        if not url or urlparse(url).scheme not in {"http", "https"}:
            continue
        item["url"] = url
        ctx.context.searched_urls.add(url)
        normalized_results.append(item)

    response["result"] = normalized_results
    return json.dumps(response, ensure_ascii=True, default=str)


@function_tool
def fetch_page(ctx: RunContextWrapper[ResearchContext], url: str, query: str) -> str:
    """Fetch and relevance-rank a URL returned by this run's web search."""
    _require_searched_url(ctx.context, url)

    from tools.fetch_url import fetch_url

    response = fetch_url(url, query, max_chunks=3)
    if isinstance(response, dict) and response.get("status") == "success":
        chunks = response.get("result", [])
        for chunk in chunks:
            chunk["content"] = chunk.get("content", "")[:3000]
        ctx.context.add_recent_info(chunks)
    return json.dumps(response, ensure_ascii=True, default=str)


def _require_searched_url(context: ResearchContext, url: str) -> None:
    if url not in context.searched_urls:
        raise ValueError("Fetch is limited to URLs returned by this run's web search.")


RESEARCH_TOOLS = [search_web, fetch_page]
