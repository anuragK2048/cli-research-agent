from google import genai
from pydantic import BaseModel, Field
from time import perf_counter

class SearchResult(BaseModel):
    title: str
    url: str
    summary: str
    relevance: float = Field(ge=0, le=1)


class SearchResponse(BaseModel):
    results: list[SearchResult]

start_time = perf_counter()

client = genai.Client()

response = client.models.generate_content(
    # model="gemini-3.1-flash-lite",
    # model="gemini-3-flash-preview",
    model="gemini-3.5-flash-lite",
    # model="gemini-3.5-flash",
    contents="Find the best Python resources for learning AI agents.",
    config={
        "response_mime_type": "application/json",
        "response_schema": SearchResponse,
    },
)

result = response.parsed

print(result)
print(result.results[0].title)
print("elapsed Time: ", round(perf_counter() - start_time, 2))