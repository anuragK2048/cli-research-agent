import json

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from time import perf_counter
from config import MAX_WEB_SEARCH_RESULTS

def web_search(query: str, max_results: int = MAX_WEB_SEARCH_RESULTS) -> dict:
    print("TOOL CALL ☎️ web_search", "arg: ", query)
    normalized_query = query.strip()
    if not query or not query.strip():
            raise ValueError("query must not be empty")
    if max_results < 1:
        raise ValueError("max_results must be at least 1")

    start_time = perf_counter()

    try:
        search_results = list(DDGS().text(normalized_query, max_results=max_results))
    except DDGSException as error:
         print(f"Error in web_search:  {str(error)}")
         return {
            "query": normalized_query,
            "status": "error",
            "result": [],
            "error": str(error),
            "elapsed_time": round(perf_counter() - start_time, 2)
         }

    return {
        "query": normalized_query,
        "status": "success",
        "result": search_results,
        "error": "",
        "elapsed_time": round(perf_counter() - start_time, 2)
    }

if __name__ == "__main__":
     print(json.dumps(web_search("Indian stock market today reasons", 10), indent=2))