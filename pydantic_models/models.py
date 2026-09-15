from pydantic import BaseModel
from typing import Literal, Optional, Any, Union


class SaveNotesArgs(BaseModel):
   key: str
   content: str
   source: str

class ReadNotesArgs(BaseModel):
   key: str

class WebSearchArgs(BaseModel):
   query: str

class FetchUrlArgs(BaseModel):
   url: str

class ToolCall(BaseModel):
  tool_call_id: str
  name: str
  args: Union[WebSearchArgs, FetchUrlArgs, SaveNotesArgs, ReadNotesArgs]

class ActionSchema(BaseModel):
  description: str
  tool_calls: list[ToolCall]

class ChatOutput(BaseModel):
  type: Literal["question", "answer"] = "answer"
  content: str

class ChatMessage(BaseModel):
  role: Literal["system", "user", "assistant", "tool"]
  content: str
  tool_call_id: str | None = None

class RecentInformation(BaseModel):
   content: str
   source: str

class contextState(BaseModel):
    goal: str
    plan: list[str]
    current_plan_step: int
    completed_actions: list[str]
    recent_info: list[RecentInformation]
    stored_notes: list[str]
    status: Literal["planning", "researching", "structuring", "completed", "pending"]

class LLMOutput(BaseModel):
  chat_output: Optional[ChatOutput] = None
  action: Optional[ActionSchema] = None
  cur_state: contextState



class State(BaseModel):
    goal: str
    plan: list[str]
    current_plan_step: int
    completed_actions: list[str]
    messages: list[ChatMessage]
    recent_info: list[RecentInformation]
    stored_notes: list[str]
    status: Literal["planning", "researching", "structuring", "completed", "pending"]
    errors: list[str]
    tool_calls: list[ToolCall]
    iteration: int

class Information(BaseModel):
   source: str
   content: str
   time_stamp: str

class StoredNotes(BaseModel):
   key: Information

class ToolResult(BaseModel):
    tool_call_id: str
    status: str
    result: Any


# {
#   "$defs": {
#     "ActionSchema": {
#       "properties": {
#         "description": {
#           "title": "Description",
#           "type": "string"
#         },
#         "status": {
#           "default": "pending",
#           "enum": [
#             "running",
#             "completed",
#             "pending",
#             "error"
#           ],
#           "title": "Status",
#           "type": "string"
#         },
#         "tool_calls": {
#           "items": {
#             "$ref": "#/$defs/ToolCall"
#           },
#           "title": "Tool Calls",
#           "type": "array"
#         }
#       },
#       "required": [
#         "description",
#         "tool_calls"
#       ],
#       "title": "ActionSchema",
#       "type": "object"
#     },
#     "ChatOutput": {
#       "properties": {
#         "type": {
#           "default": "answer",
#           "enum": [
#             "question",
#             "answer"
#           ],
#           "title": "Type",
#           "type": "string"
#         },
#         "content": {
#           "title": "Content",
#           "type": "string"
#         }
#       },
#       "required": [
#         "content"
#       ],
#       "title": "ChatOutput",
#       "type": "object"
#     },
#     "RecentInformation": {
#       "properties": {
#         "content": {
#           "title": "Content",
#           "type": "string"
#         },
#         "source": {
#           "title": "Source",
#           "type": "string"
#         }
#       },
#       "required": [
#         "content",
#         "source"
#       ],
#       "title": "RecentInformation",
#       "type": "object"
#     },
#     "ToolCall": {
#       "properties": {
#         "tool_call_id": {
#           "title": "Tool Call Id",
#           "type": "string"
#         },
#         "name": {
#           "title": "Name",
#           "type": "string"
#         },
#         "args": {
#           "additionalProperties": true,
#           "title": "Args",
#           "type": "object"
#         }
#       },
#       "required": [
#         "tool_call_id",
#         "name",
#         "args"
#       ],
#       "title": "ToolCall",
#       "type": "object"
#     },
#     "contextState": {
#       "properties": {
#         "goal": {
#           "title": "Goal",
#           "type": "string"
#         },
#         "plan": {
#           "items": {
#             "type": "string"
#           },
#           "title": "Plan",
#           "type": "array"
#         },
#         "current_plan_step": {
#           "title": "Current Plan Step",
#           "type": "integer"
#         },
#         "completed_actions": {
#           "items": {
#             "type": "string"
#           },
#           "title": "Completed Actions",
#           "type": "array"
#         },
#         "recent_info": {
#           "items": {
#             "$ref": "#/$defs/RecentInformation"
#           },
#           "title": "Recent Info",
#           "type": "array"
#         },
#         "stored_notes": {
#           "items": {
#             "type": "string"
#           },
#           "title": "Stored Notes",
#           "type": "array"
#         },
#         "status": {
#           "enum": [
#             "planning",
#             "researching",
#             "structuring",
#             "completed",
#             "pending"
#           ],
#           "title": "Status",
#           "type": "string"
#         }
#       },
#       "required": [
#         "goal",
#         "plan",
#         "current_plan_step",
#         "completed_actions",
#         "recent_info",
#         "stored_notes",
#         "status"
#       ],
#       "title": "contextState",
#       "type": "object"
#     }
#   },
#   "properties": {
#     "chat_output": {
#       "anyOf": [
#         {
#           "$ref": "#/$defs/ChatOutput"
#         },
#         {
#           "type": "null"
#         }
#       ],
#       "default": null
#     },
#     "action": {
#       "anyOf": [
#         {
#           "$ref": "#/$defs/ActionSchema"
#         },
#         {
#           "type": "null"
#         }
#       ],
#       "default": null
#     },
#     "cur_state": {
#       "$ref": "#/$defs/contextState"
#     }
#   },
#   "required": [
#     "cur_state"
#   ],
#   "title": "LLMOutput",
#   "type": "object"
# }