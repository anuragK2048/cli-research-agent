from ollama import chat
from ollama import ChatResponse
import json
from pydantic import BaseModel
from typing import Literal, Optional
from pydantic_models.models import LLMOutput
from google import genai
# from groq import Groq

import os
from ollama import Client

ollama_api_key = os.environ.get('OLLAMA_API_KEY')
client_headers = {}
if ollama_api_key:
  client_headers['Authorization'] = 'Bearer ' + ollama_api_key

client = Client(
    host='https://ollama.com',
    headers=client_headers
)

gemini_client = genai.Client()
# groq_client = Groq()

def askLLM(messages):
  response = chat(
    model='gemma3:1b',
    # model='ornith:9b',
    messages=messages,
    format=LLMOutput.model_json_schema(),  # Use Pydantic to generate the schema or format=schema
    options={'temperature': 0},  # Make responses more deterministic
  )
  return LLMOutput.model_validate_json(response.message.content).model_dump()

def askCloudLLM(messages):
  with open("storage/messages_log.json", "w") as f:
      json.dump(messages, f, indent=2, ensure_ascii=False)
  response = client.chat('gemma4:31b-cloud', messages=messages, format=LLMOutput.model_json_schema(), options={'temperature': 0}, stream=False)
  # response = client.chat('gpt-oss:120b', messages=messages, format=LLMOutput.model_json_schema(), options={'temperature': 0}, stream=False)
  # response = client.chat('nemotron-3-ultra', messages=messages, format=LLMOutput.model_json_schema(), options={'temperature': 0}, stream=False, think=False)
  content = response["message"]["content"]

  print({
    "done": response.get("done"),
    "done_reason": response.get("done_reason"),
    "prompt_eval_count": response.get("prompt_eval_count"),
    "eval_count": response.get("eval_count"),
    "message": response.get("message"),
  })

  try:
    with open("storage/raw_llm_output.json", "r") as f:
      llm_log = json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
      llm_log = []

  try:
      parsed = json.loads(content)
  except json.JSONDecodeError as e:
      print("JSON error:", e)
      print("Position:", e.pos)
      print("Column:", e.colno)
      print("Content length:", len(content))

      if content:
          print("Around error:", repr(
              content[max(0, e.pos - 200):e.pos + 200]
          ))
          print(
              "Character:",
              repr(content[e.pos]) if e.pos < len(content) else "<EOF>"
          )
      else:
          print("Content is completely empty")

      # raise
      parsed = f"JSON error: {e}"

  llm_log.append({"raw": content, "repr": repr(content), "raw_length": len(content), "parsed_pretty": parsed})

  with open("storage/raw_llm_output.json", "w") as f:
    json.dump(llm_log, f, indent=2, ensure_ascii=False)

  try:
    return LLMOutput.model_validate_json(content).model_dump()

  except Exception as e:
      # print("JSON/Pydantic error:", e)
      # print("Response length:", len(content))

      # if hasattr(e, "errors"):
      #     print(e.errors())
      raise


def askGemini(messages):
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

  response = gemini_client.models.generate_content(
    # model="gemini-3.5-flash",
    model="gemini-3.5-flash-lite",
    contents=contents,
    config={
        "response_mime_type": "application/json",
        "response_schema": LLMOutput,
        "system_instruction": system_instruction,
    },
  )
  print(response.parsed)
  return response.parsed.model_dump()


# def askGroq(messages):
#   response = groq_client.chat.completions.create(
#       model="openai/gpt-oss-120b",
#       messages=messages,
#       temperature=1,
#       max_completion_tokens=2031,
#       top_p=1,
#       reasoning_effort="medium",
#       stream=False,
#       response_format={"type": "json_schema", "json_schema": {"name": "sql_query_generation", "schema": LLMOutput.model_json_schema()}},
#       stop=None,
#       tools=[]
#   )

#   content = response.choices[0].message.content or "{}"
#   try:
#       with open("storage/raw_llm_output.json", "r") as f:
#         llm_log = json.load(f)
#   except (FileNotFoundError, json.JSONDecodeError):
#         llm_log = []
  
#   try:
#       # parsed = json.loads(content)
#       parsed = json.loads(content)
#   except json.JSONDecodeError as e:
#       print("JSON error:", e)
#       print("Position:", e.pos)
#       print("Column:", e.colno)
#       print("Content length:", len(content))

#       if content:
#           print("Around error:", repr(
#               content[max(0, e.pos - 200):e.pos + 200]
#           ))
#           print(
#               "Character:",
#               repr(content[e.pos]) if e.pos < len(content) else "<EOF>"
#           )
#       else:
#           print("Content is completely empty")

#       # raise
#       parsed = f"JSON error: {e}"

#   llm_log.append({"raw": content, "repr": repr(content), "raw_length": len(content), "parsed_pretty": parsed})

#   with open("storage/raw_llm_output.json", "w") as f:
#     json.dump(llm_log, f, indent=2, ensure_ascii=False)

#   try:
#     return LLMOutput.model_validate_json(content).model_dump()

#   except Exception as e:
#       # print("JSON/Pydantic error:", e)
#       # print("Response length:", len(content))

#       # if hasattr(e, "errors"):
#       #     print(e.errors())
#       raise

