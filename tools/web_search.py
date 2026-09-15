from datetime import datetime
from time import perf_counter
from typing import Any

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from .chunking import chunk
from .embedding import embed, similarity_ranking
from .fetchUrl.page_fetcher import PageFetcher


def web_search(
    query: str,
    max_results: int = 7,
    max_chunks: int = 3,
) -> dict[str, Any]:
    print("TOOL CALL ☎️ web_search", "arg: ", query)
    """Search, fetch, and rank web content for an LLM tool call."""
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if max_results < 1:
        raise ValueError("max_results must be at least 1")
    if max_chunks < 1:
        raise ValueError("max_chunks must be at least 1")

    started_at = datetime.now().isoformat(timespec="seconds")
    start_time = perf_counter()
    normalized_query = query.strip()

    try:
        search_results = list(DDGS().text(normalized_query, max_results=max_results))
    except DDGSException as error:
        return {
            "query": normalized_query,
            "status": "error",
            "error": str(error),
            "top_chunks": [],
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "elapsed_seconds": round(perf_counter() - start_time, 2),
        }
    page_results = []

    fetcher = PageFetcher()
    try:
        for result in search_results:
            url = result.get("href") or result.get("url")
            if not url:
                continue
            page = fetcher.fetch(url).to_dict()
            if page.get("content"):
                page_results.append(page)
    finally:
        fetcher.close()

    all_chunks = []
    for page in page_results:
        all_chunks.extend(chunk(page))

    sorted_chunks = []
    if all_chunks:
        content_embeddings = embed([item["content"] for item in all_chunks])
        query_embedding = embed(normalized_query)

        for match in similarity_ranking(content_embeddings, query_embedding):
            all_chunks[match["corpus_id"]]["cosine_score"] = float(match["score"])

        sorted_chunks = sorted(
            all_chunks,
            key=lambda item: item.get("cosine_score", 0.0),
            reverse=True,
        )[:max_chunks]

        top_chunks = sorted_chunks

    return {
        "query": normalized_query,
        "status": "success",
        "top_chunks": top_chunks,
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": round(perf_counter() - start_time, 2),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(web_search("multilingual embedding models RAG benchmark 2026"), indent=2))

