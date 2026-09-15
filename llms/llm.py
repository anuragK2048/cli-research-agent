import json
from pydantic import BaseModel
from typing import Literal, Optional, Any, Union
from time import perf_counter
from llms.gemini import askGemini
from llms.ollamaCloud import askCloudOllama

class LLMOutput(BaseModel):
    response_id: str
    llm_name: str
    parsed_output: Union[dict, str]
    latency: float
    token_usage: dict
    raw_output: str

class AskLLMResult(BaseModel):
    status: Literal["success", "fail"]
    output: Optional[LLMOutput] = None


availaible_llms = {
    "gemini": askGemini,
    "cloudOllama": askCloudOllama,
    # "ollama": askOllama,
}

def askLLM(messages: list, llms: list, retries: int = 2, pydantic_schema=None):
    """receives messages, list of llms for fallback priority wise, number of retries before fallback llm, pydantic schema for structured output"""
    start_time = perf_counter()

    # log messages
    with open("llms/debug/messages.json", "w") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    success = False
    for llm in llms:
        if success:
            break
        if llm not in availaible_llms:
            continue
        remaining_retries = retries
        while remaining_retries:
            result = availaible_llms[llm](messages, pydantic_schema)
            # print(result)
            if result["status"] == "success":
                output = result["output"]
                success = True
                break
            remaining_retries -= 1

            # log error
            print(f"🔴 {llm} LLM Error: ", result["output"])

    if success == True:
        total_time = round(perf_counter() - start_time, 2)
        # log llm output
        try:
            with open("llms/debug/llm_output.json", "r") as f:
                llm_log = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            llm_log = []

        llm_log.append({**output, "total_elapsed_time": total_time})

        with open("llms/debug/llm_output.json", "w") as f:
            json.dump(llm_log, f, indent=2, ensure_ascii=False)

        # log messages with response_id
        with open(f"llms/debug/{output["response_id"]}.json", "w") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

        print(output["parsed_output"])
        return output["parsed_output"]

    raise
    return "ask LLM failed"

