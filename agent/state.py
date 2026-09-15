import json
from pydantic import BaseModel
from typing import Literal, Optional
from pydantic_models.models import State
from agent.tool_executor import new_tool_calls

cur_state = {"iteration": 0, "tool_calls": [], "errors": []}

def initialize_cur_state(new_cur_context_state):
    global cur_state
    cur_state = {**cur_state, **new_cur_context_state}
    # update_display()
    plan = cur_state.get("plan", [])
    action = cur_state.get("cur_action", "")
    step = cur_state.get("current_plan_step", 0)
    
    plan = plan[step-1] if step < len(plan) else "None"
    
    print(
        f"status: {cur_state.get('status')}\n"
        f"plan_step: {step}\n"
        f"plan: {plan}\n"
        f"action: {action}"
    )

def update_cur_state(new_context_state):
    global cur_state
    new_cur_state = {**new_context_state, "iteration": cur_state["iteration"]+1, "tool_calls": cur_state["tool_calls"], "errors": cur_state["errors"]}
    cur_state = new_cur_state
    # update_display()
    plan = cur_state.get("plan", [])
    action = cur_state.get("cur_action", "")
    step = cur_state.get("current_plan_step", 0)
    
    plan = plan[step-1] if step < len(plan) else "None"
    
    print(
        f"status: {cur_state.get('status')}\n"
        f"plan_step: {step}\n"
        f"plan: {plan}\n"
        f"action: {action}"
    )

def update_tool_call_history(new_tool_calls):
    global cur_state
    cur_state["tool_calls"].extend(new_tool_calls)

def get_cur_state():
    return cur_state