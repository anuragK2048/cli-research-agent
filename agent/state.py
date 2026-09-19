import json
from pydantic import BaseModel
from typing import Literal, Optional
# from pydantic_models.models import State
# from agent.tool_executor import new_tool_calls

state = {}
recent_info = []
controversial_facts = []
verified_info = []

def add_to_verified_info(new_verified_info: list):
    verified_info.extend(new_verified_info)
    log(verified_info, "verified_info")

def get_verified_info():
    return verified_info


def add_to_controversial_facts(new_facts: list):
    controversial_facts.extend(new_facts)
    log(controversial_facts, "controversial_facts")

def get_controversial_facts():
    return controversial_facts

def reset_controversial_facts():
    controversial_facts.clear()


def add_to_recent_info(new_recent_infos: list):
    recent_info.extend(new_recent_infos)
    log(recent_info, "recent_info")

def get_recent_info():
    return recent_info

def reset_recent_info():
    recent_info.clear()


def update_cur_state(update):
    state.update(update)

def get_cur_state():
    return state


def log(data, filename):
    # with open(f"memory/{filename}.jsonl", "a") as f:
    #     f.write(json.dumps(data) + "\n")

    # try:
    #     with open(f"memory/{filename}.json", "r") as f:
    #         previous_state = json.load(f)
    # except (FileNotFoundError, json.JSONDecodeError):
    #     previous_state = []

    # previous_state.append(data)

    with open(f"memory/{filename}.json", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# cur_state = {"iteration": 0, "tool_calls": [], "errors": []}

# def initialize_cur_state(new_cur_context_state):
#     global cur_state
#     cur_state = {**cur_state, **new_cur_context_state}
#     # update_display()
#     plan = cur_state.get("plan", [])
#     action = cur_state.get("cur_action", "")
#     step = cur_state.get("current_plan_step", 0)
    
#     plan = plan[step-1] if step < len(plan) else "None"
    
#     print(
#         f"status: {cur_state.get('status')}\n"
#         f"plan_step: {step}\n"
#         f"plan: {plan}\n"
#         f"action: {action}"
#     )

# def update_cur_state(new_context_state):
#     global cur_state
#     new_cur_state = {**new_context_state, "iteration": cur_state["iteration"]+1, "tool_calls": cur_state["tool_calls"], "errors": cur_state["errors"]}
#     cur_state = new_cur_state
#     # update_display()
#     plan = cur_state.get("plan", [])
#     action = cur_state.get("cur_action", "")
#     step = cur_state.get("current_plan_step", 0)
    
#     plan = plan[step-1] if step < len(plan) else "None"
    
#     print(
#         f"status: {cur_state.get('status')}\n"
#         f"plan_step: {step}\n"
#         f"plan: {plan}\n"
#         f"action: {action}"
#     )

# def update_tool_call_history(new_tool_calls):
#     global cur_state
#     cur_state["tool_calls"].extend(new_tool_calls)

# def get_cur_state():
#     return cur_state