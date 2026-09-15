from groq import Groq
from pydantic import BaseModel, Field, ConfigDict
import json

class ValidationStatus(BaseModel):
    is_valid: bool
    syntax_errors: list[str]

class SQLQueryGeneration(BaseModel):
    query: str
    query_type: str
    tables_used: list[str]
    estimated_complexity: str
    execution_notes: list[str]
    validation_status: ValidationStatus

    # model_config = ConfigDict(extra="forbid")
class SearchResult(BaseModel):
    title: str
    url: str
    summary: str
    relevance: float = Field(ge=0, le=1)


class SearchResponse(BaseModel):
    results: list[SearchResult]

client = Groq()
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
      {
        "role": "user",
        "content": "hi\n"
      },
      {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      {
        "role": "user",
        "content": "Whats your name"
      }
    ],
    temperature=1,
    max_completion_tokens=2031,
    top_p=1,
    reasoning_effort="medium",
    stream=False,
    response_format={"type": "json_schema", "json_schema": {"name": "sql_query_generation", "schema":SearchResponse.model_json_schema()}},
    stop=None,
    tools=[]
)

result = json.loads(response.choices[0].message.content or "{}")
print(json.dumps(result, indent=2))


# print(json.dumps(SearchResponse.model_json_schema(), indent=2))
# print(json.dumps(SQLQueryGeneration.model_json_schema(), indent=2))