import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm import askLLM, askCloudLLM, askGemini, askGroq
from prompts.system import system_prompt, system_promptChatGPT
from pydantic_models.models import LLMOutput
from agent.handleLLMoutput import processOutput
from agent.state import initialize_cur_state, update_cur_state
from agent.state import get_cur_state

# messages = [{'role': 'system', 'content': system_prompt}]
messages = [{'role': 'system', 'content': system_promptChatGPT}]

while True:
    # user_input = input("> ")
    user_input = "Compare the best cloud providers for deploying an AI startup in India, considering cost, GPU availability, and managed services."
    messages.append({"role": "user", "content": user_input})
    llm_output = askGemini(messages)
    messages.append({"role": "assistant", "content": json.dumps(llm_output)})

    # classify llm_output
    if llm_output["chat_output"] != None:
        print(llm_output["chat_output"]["content"])

    if llm_output["cur_state"] != None and "plan" not in get_cur_state():
        initialize_cur_state(llm_output["cur_state"])

    if llm_output["action"] is None and llm_output["chat_output"] is None and llm_output["cur_state"] is not None and llm_output["cur_state"]["status"] != "completed":
        print("HHHH" * 40)
        messages.append({"role": "user", "content": "populate action property of json with required tool calls"})
        llm_output = askGemini(messages)
        messages.append({"role": "assistant", "content": json.dumps(llm_output)})

    if llm_output["action"] != None:
        # researching
        while True:
            action_result = processOutput(llm_output)
            messages.append({"role": "assistant", "content":json.dumps(action_result)})
            llm_output = askGemini(messages)

            # ask clarifying question in between
            if llm_output["chat_output"] is not None and llm_output["cur_state"]["status"] != "completed": 
                print(llm_output["chat_output"]["content"])
                user_input = input("> ")
                messages.append({"role": "user", "content": user_input})
                llm_output = askGemini(messages)

            if llm_output["action"] is None and llm_output["cur_state"]["status"] == "completed":
                break

            cur_iterations = get_cur_state()["iteration"]
            if cur_iterations > 20:
                print("actions limit exceeded 🔴🔴🔴")
                break

        if llm_output["chat_output"] is not None: 
            print(f'Final ResearchResult: {llm_output["chat_output"]["content"]}')
            print(get_cur_state()["tool_calls"])
            input("> ")
            # tools = [tool for tool in get_cur_state()["tool_calls"]]
            # tools_text = "\n".join(tools) if tools else "None"

            # print(f"Tools Used:\n{tools_text}")

        
