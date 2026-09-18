import json
from time import perf_counter
import uuid

from tools.fetchUrl.chunking import chunk
from tools.fetchUrl.embedding import embed, similarity_ranking

from .fetchUrl.page_fetcher import PageFetcher
from config import MAX_FETCH_URL_CHUNKS

def fetch_url(url: str, query: str, max_chunks: int = MAX_FETCH_URL_CHUNKS) -> dict:
    print("TOOL CALL ☎️ fetch_url", "arg: ", url)
    start_time = perf_counter()


    fetcher = PageFetcher()
    try:
        if not url:
            return "No url provided"
        page = fetcher.fetch(url).to_dict()
        if page.get("content") and page["status_code"] == 200:
            chunks = chunk(page) 

            content_embeddings = embed([item["content"] for item in chunks])
            query_embedding = embed(query)

            for match in similarity_ranking(content_embeddings, query_embedding):
                chunks[match["corpus_id"]]["cosine_score"] = float(match["score"])
            # each chunk have cosine_score

            sorted_chunks = sorted(
                chunks,
                key=lambda item: item.get("cosine_score", 0.0),
                reverse=True,
            )[:max_chunks]

            sorted_chunks_content = [{"chunk_id": str(uuid.uuid4()), "url": chunk["url"], "query": query, "title": chunk["title"], "content": chunk["content"]} for chunk in sorted_chunks]

            return {
                "url": url,
                "status": "success",
                "query": query,
                "result": sorted_chunks_content,
                "error": "",
                "elapsed_time": round(perf_counter() - start_time, 2)
            }

            
        else: 
            return {
                "url": url,
                "status": "error",
                "query": query,
                "result": [],
                "error": f"Unable to fetch {url}, {page["error"]}",
                "elapsed_time": round(perf_counter() - start_time, 2)
            }

    finally:
        fetcher.close()

if __name__ == "__main__":
    print(json.dumps(fetch_url("https://pulse.zerodha.com/", "Indian stock market today reasons"), indent=2))
