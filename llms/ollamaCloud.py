import json
from time import perf_counter
from ollama import chat
from ollama import Client
import os
import uuid

models = ["gpt-oss:120b", "gemma4:31b-cloud", "nemotron-3-ultra"]

ollama_api_key = os.environ.get('OLLAMA_API_KEY')
client_headers = {}
if ollama_api_key:
  client_headers['Authorization'] = 'Bearer ' + ollama_api_key

client = Client(
    host='https://ollama.com',
    headers=client_headers
)

def askCloudOllama(messages, pydantic_schema=None):
    """Generate output from Cloud LLM with optional Pydantic structured output."""

    start_time = perf_counter()

    try:
        config = {
            "options": {
                "temperature": 0
            },
            "stream": False
        }

        # Add structured output schema if provided
        if pydantic_schema is not None:
            config["format"] = pydantic_schema.model_json_schema()

        response = client.chat(
            models[1],
            messages=messages,
            **config
        )

    except Exception as e:
        return {"status": "fail", "output": str(e)}

    try:
        content = response["message"]["content"]

        # Parse structured output
        if pydantic_schema is not None:
            parsed_output = pydantic_schema.model_validate_json(content).model_dump()
        else:
            parsed_output = content

        output = {
            "llm_name": models[0],
            "response_id": str(uuid.uuid4()),
            "parsed_output": parsed_output,
            "latency": round(perf_counter() - start_time, 2),
            "token_usage": {
                "input_tokens": response.get("prompt_eval_count"),
                "output_tokens": response.get("eval_count"),
                "total_tokens": (
                    (response.get("prompt_eval_count") or 0)
                    + (response.get("eval_count") or 0)
                ),
            },
            "raw_output": content
        }

        return {
            "status": "success",
            "output": output
        }

    except Exception as e:
       return {"status": "fail", "output": str(e)}