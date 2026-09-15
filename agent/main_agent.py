import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm import askLLM, askCloudLLM, askGemini
from prompts.system import system_prompt
from pydantic_models.models import LLMOutput
from agent.handleLLMoutput import processOutput
from agent.state import initialize_cur_state

messages = [{'role': 'system', 'content': system_prompt}]
iteration = 0

def process(role, content):
    messages.append({'role': role, 'content': content})
    print("(((" * 60)
    print(json.dumps(messages, indent=2))
    print(")))" * 60)
    return askGemini(messages)
    # return askCloudLLM(messages)
    # return askLLM(messages)

while True:
    user_input = input("> ")

    if user_input == "/bye":
        break

    output = process("user", user_input)
    messages.append({'role': 'assistant', 'content': json.dumps(output)})

    while True:
        if output["chat_output"] != None:
            print(output["chat_output"]["content"])
            user_input = input("> ")
            if user_input == "/bye":
                break
            continue

        if output["cur_state"] != None and output["cur_state"]["status"] != "completed":
            initialize_cur_state(output["cur_state"])
            output = process("user", "start research")
            messages.append({'role': 'assistant', 'content': json.dumps(output)})

        while output["action"] is not None and output["cur_state"] != None and output["cur_state"]["status"] != "completed":
            iteration += 1
            newInput = processOutput(output)
            output = process("assistant", json.dumps(newInput))
            messages.append({'role': 'assistant', 'content': json.dumps(output)})
            print("*" * 30, "ITERATIONS = ", iteration)
            # print(json.dumps(output, indent=2))
        
