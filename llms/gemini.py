from google import genai
from pydantic import BaseModel, Field
from time import perf_counter
import json

models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3-flash-preview"]

client = genai.Client()

def askGemini(messages, pydantic_schema):
    """return structured output from gemini llm's"""
    start_time = perf_counter()

    # structure messages acc to gemini format
    system_instruction = None
    contents = []

    for message in messages:
      role = message['role']
      content = str(message['content'])
    
      if role == 'system':
        system_instruction = content
        continue
    
      gemini_role = 'model' if role == 'assistant' else 'user'
      if contents and contents[-1]['role'] == gemini_role:
        contents[-1]['parts'][0]['text'] += '\n' + content
      else:
        contents.append({
          'role': gemini_role,
          'parts': [{'text': content}],
        })
    
    if contents and contents[-1]['role'] == 'model':
       contents.append({
          'role': 'user',
          'parts': [{'text': 'Please continue.'}]
       })

    # response generation
    try:
        if pydantic_schema is not None:
            response = client.models.generate_content(
                model=models[3],
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": pydantic_schema,
                    "system_instruction": system_instruction,
                },
            )
        else:
            response = client.models.generate_content(
                model=models[0],
                contents=contents,
                config={
                    "system_instruction": system_instruction,
                },
            )

        parsed_output = (
            response.parsed.model_dump()
            if response.parsed is not None
            else response.text
        )

    except Exception as e:
       return {"status": "fail", "output": str(e)}

    try:
        pydantic_schema.model_validate(response.parsed)
        output = {
            "response_id": response.response_id,
            "llm_name": response.model_version,
            "parsed_output": parsed_output,
            "latency": round(perf_counter() - start_time, 2),
            "token_usage": {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
                "thoughts_tokens": getattr(
                    response.usage_metadata,
                    "thoughts_token_count",
                    None
                ),
            },
            "raw_output": response.text
        }
        return {"status": "success", "output": output}
    
    except Exception as e:
       return {"status": "fail", "output": f"JSON/Pydantic error: {e}"}
       


# print(json.dumps(output, indent=2))