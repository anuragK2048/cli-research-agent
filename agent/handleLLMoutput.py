import json
from agent.state import update_cur_state, add_to_recent_info
from tools.web_search import web_search
from tools.fetch_url import fetch_url
from tools.notes import save_info, read_info

tool_registry = {
    "web_search": {
        "function": web_search,
        "description": "Search the web for information",
        "parameters": {
            "query": "string"
        }
    },
    "fetch_url": {
        "function": fetch_url,
        "description": "Fetch content from a url",
        "parameters": {
            "url": "string"
        }
    },
#     "save_info": {
#         "function": save_info,
#         "description": "Save important points in notes file",
#         "parameters": {
#             "key": "string",
#             "content": "string",
#             "source": "string"
#         }
#     },
#     "read_info": {
#         "function": read_info,
#         "description": "Retrieve important points from notes file",
#         "parameters": {
#             "key": "string"
#         }
#     },
}

def processOutput(stage, LLM_output):

    if stage == "scope":
        if "research_scope" in LLM_output:
            update_cur_state({"research_scope": LLM_output["research_scope"]})
        else:
            raise

    if stage == "plan":
        if "sub_topics" in LLM_output:
            update_cur_state({"sub_topics": LLM_output["sub_topics"]})
        else:
            raise

    if stage == "discover":
        if "tool_calls" in LLM_output is not None:
            tool_calls_output = []
            # print(LLM_output)
            tool_calls = LLM_output["tool_calls"]
            if len(tool_calls) != 0:
                for use_tool in tool_calls:
                    # update_tool_call_history([use_tool["name"], use_tool["args"]])
                    tool = tool_registry[use_tool["name"]]
                    output = tool["function"](**use_tool["args"])
                    # save chunks in recent_info
                    if use_tool["name"] == "fetch_url":
                        add_to_recent_info(output["result"])
                        tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": "saved top relevant chunks from this webpage"})
                    else:
                        tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": output})

            return {"tool_call_result": tool_calls_output}
        
        # else:
        #     raise

    # print("LLM OUTPUT", "+" * 30)
    # print(json.dumps(LLM_output, indent=2, ensure_ascii=False))

    # new_context_state = LLM_output["cur_state"]
    # cur_action = LLM_output["action"]["description"] if LLM_output["action"] is not None else ""
    # update_cur_state({**new_context_state, "cur_action": cur_action})

    # # handling tool call
    # tool_calls_output = []
    # if LLM_output["action"] is not None:
    #     tool_calls = LLM_output["action"]["tool_calls"]
    #     if len(tool_calls) != 0:
    #         for use_tool in tool_calls:
    #             update_tool_call_history([use_tool["name"], use_tool["args"]])
    #             tool = tool_registry[use_tool["name"]]
    #             output = tool["function"](**use_tool["args"])
    #             tool_calls_output.append({"tool_call_id": use_tool["tool_call_id"], "status": "success", "result": output})
        
    #     return {"action_result": tool_calls_output}

    # else:
    #     return {"action_result": "Not Applicable, Proceed further with output"}
    
    # determine the current state, update the cur_state
    # determine the tool calls, execute them and map the results with tool_id
    # see if the LLM is trying to have chat_output
     