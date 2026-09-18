import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.generate_user_prompt import generate_user_prompt
from llms.llm import askLLM
from pydantic_models.models import DiscoverWebOutput, PlanOutput, ScopeOutput
from agent.handleLLMoutput import processOutput
from agent.state import update_cur_state
from agent.state import get_cur_state
from prompts.system_prompts import system_prompts


llm_stages_config = {
    "scope": {
        "system_prompt": system_prompts["scope"],
        "context_inputs": "",
        "output_schema": ScopeOutput
    },
    "plan": {
        "system_prompt": system_prompts["plan"],
        "context_inputs": "research_scope",
        "output_schema": PlanOutput
    },
    "discover": {
        "system_prompt": system_prompts["discover"],
        "context_inputs": "sub_topic",
        "output_schema": DiscoverWebOutput
    },
    "research.retrieval": {
        "system_prompt": "",
        "context_inputs": "plan.sub-topic, topic checklist",
        # "output_schema": LLMOutput
    },
}


askLLMConfig = {
    "llms": ["gemini", "cloudOllama"],
    "retries": 3,
}



messages = []
messages.append({"role": "system", "content": llm_stages_config["scope"]["system_prompt"]})

# scope
while True:
    # user_input = input("> ")
    user_input = "Compare the best cloud providers for deploying an AI startup in India, considering cost, GPU availability, and managed services"
    messages.append({"role": "user", "content": user_input})
    output = askLLM(messages, llm_stages_config["scope"]["output_schema"])
    if output["chat"] is not None:
        print(">> ", output["chat"])
        messages.append({"role": "assistant", "content": output["chat"]})
    if output["status"] == "completed":
        processOutput("scope", output)
        # plan
        messages = []
        messages.append({"role": "system", "content": llm_stages_config["plan"]["system_prompt"]})
        messages.append({"role": "user", "content": generate_user_prompt("plan", {"research_scope": get_cur_state()["research_scope"]})})
        output = askLLM(messages, llm_stages_config["plan"]["output_schema"])
        print(json.dumps(output["sub_topics"], indent=2))
        # print("Confirm this plan?")
        # user_input = input('>>>>> "Yes" or "No"')
        # if user_input == "No":
        #     messages.append({"role": "assistant", "content": output})
        #     messages.append({"role": "user", "content": "I want change in the current plan. Do requirement gathering again"})
        #     print("> What else do you want?")
        # if user_input == "Yes":
        if True:
            processOutput("plan", output)

            # research stage
            for sub_topic in get_cur_state()["sub_topics"]:
                # discover
                messages = []
                messages.append({"role": "system", "content": llm_stages_config["discover"]["system_prompt"]})
                messages.append({"role": "user", "content": generate_user_prompt("discover", {"sub_topic": json.dumps(sub_topic)})})
                output = askLLM(messages, llm_stages_config["discover"]["output_schema"])
                # print(output)
                while output["status"] != "completed":
                    result = processOutput("discover", output)
                    messages.append({"role": "user", "content": json.dumps(result)})
                    output = askLLM(messages, llm_stages_config["discover"]["output_schema"])

            print("DONEEEEEE")
            break

                # flag
                # messages = []





        













# messages = [{'role': 'system', 'content': system_prompt}]
# messages = [{'role': 'system', 'content': system_promptChatGPT}]

# while True:
#     user_input = input("> ")
#     # user_input = "Compare the best cloud providers for deploying an AI startup in India, considering cost, GPU availability, and managed services."
#     messages.append({"role": "user", "content": user_input})
#     llm_output = askLLM(messages, askLLMConfig["scheme"], askLLMConfig["llms"], askLLMConfig["retries"])
#     # print(llm_output)
#     messages.append({"role": "assistant", "content": json.dumps(llm_output)})

#     # classify llm_output
#     if llm_output["chat_output"] != None:
#         print(llm_output["chat_output"]["content"])

#     if llm_output["cur_state"] != None and "plan" not in get_cur_state():
#         initialize_cur_state(llm_output["cur_state"])

#     if llm_output["action"] is None and llm_output["chat_output"] is None and llm_output["cur_state"] is not None and llm_output["cur_state"]["status"] != "completed":
#         print("HHHH" * 40)
#         messages.append({"role": "user", "content": "populate action property of json with required tool calls"})
#         llm_output = askLLM(messages, askLLMConfig["scheme"], askLLMConfig["llms"], askLLMConfig["retries"])
#         messages.append({"role": "assistant", "content": json.dumps(llm_output)})

#     if llm_output["action"] != None:
#         # researching
#         while True:
#             action_result = processOutput(llm_output)
#             messages.append({"role": "assistant", "content":json.dumps(action_result)})
#             llm_output = askLLM(messages, askLLMConfig["scheme"], askLLMConfig["llms"], askLLMConfig["retries"])

#             # ask clarifying question in between
#             if llm_output["chat_output"] is not None and llm_output["cur_state"]["status"] != "completed": 
#                 print(llm_output["chat_output"]["content"])
#                 user_input = input("> ")
#                 messages.append({"role": "user", "content": user_input})
#                 llm_output = askLLM(messages, askLLMConfig["scheme"], askLLMConfig["llms"], askLLMConfig["retries"])

#             if llm_output["action"] is None and llm_output["cur_state"]["status"] == "completed":
#                 break

#             cur_iterations = get_cur_state()["iteration"]
#             if cur_iterations > 20:
#                 print("actions limit exceeded 🔴🔴🔴")
#                 break

#         if llm_output["chat_output"] is not None: 
#             print(f'Final ResearchResult: {llm_output["chat_output"]["content"]}')
#             print(get_cur_state()["tool_calls"])
#             input("> ")
#             # tools = [tool for tool in get_cur_state()["tool_calls"]]
#             # tools_text = "\n".join(tools) if tools else "None"

#             # print(f"Tools Used:\n{tools_text}")

        
