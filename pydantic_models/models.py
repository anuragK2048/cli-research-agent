from pydantic import BaseModel
from typing import Literal, Optional, Any, Union, List

# LLM Output

class ResearchScopeOutput(BaseModel):
   goal: str
   requirements: List[str]

class ScopeOutput(BaseModel):
   status: Literal["in-progress", "completed"]
   chat: str | None = None
   research_scope: ResearchScopeOutput | None = None

class SubTopic(BaseModel):
   name: str
   check_list: List[str]

class PlanOutput(BaseModel):
   sub_topics: List[SubTopic]


# Research Phase

# TOOLS
class WebSearchArgs(BaseModel):
   query: str

class FetchUrlArgs(BaseModel):
   url: str
   query: str

class ToolCall(BaseModel):
   id: str
   name: Literal["web_search", "fetch_url"]
   args: Union[WebSearchArgs, FetchUrlArgs]

class DiscoverWebOutput(BaseModel):
   chat: str | None = None
   status: Literal["in-progress", "completed"]
   tool_calls: List[ToolCall] | None = None

class FlaggedFact(BaseModel):
   fact_id: str
   claim: str
   source_chunk_ids: list[str]
   reason: str
   materiality: Literal["high", "low"] = "low"

class FlagOutput(BaseModel):
   controversial_facts: List[FlaggedFact]


# Verification phase

class EvidenceFor(BaseModel):
   chunk_id: str
   source_type: Literal["primary", "secondary", "unknown"]
   stance_strength: Literal["direct", "indirect", "partial"]
   supports: str

class CorroborateSingleOutput(BaseModel):
   tool_calls: List[ToolCall] | None = None
   evidence_for: List[EvidenceFor] | None = None

class BatchedEvidencesFor(BaseModel):
   fact_id: str
   evidence_for: List[EvidenceFor]

class CorroborateBatchOutput(BaseModel):
   tool_calls: List[ToolCall] | None = None
   result: List[BatchedEvidencesFor]


class EvidenceAgainst(BaseModel):
   chunk_id: str
   source_type: Literal["primary", "secondary", "unknown"]
   stance_strength: Literal["direct", "indirect", "partial"]
   contradicts: str

class ChallengeSingleOutput(BaseModel):
   tool_calls: List[ToolCall] | None = None
   evidence_against: List[EvidenceAgainst] | None = None

class BatchedEvidencesAgainst(BaseModel):
   fact_id: str
   evidence_against: List[EvidenceAgainst]

class ChallengeBatchOutput(BaseModel):
   tool_calls: List[ToolCall] | None = None
   result: List[BatchedEvidencesAgainst]


class FactAdjudicate(BaseModel):
   fact_id: str
   verdict: Literal["supported", "contradicted", "unresolved"]
   summary: str
   trust_score: float
   verdict_reason: str | None = None

class AdjudicateOutput(BaseModel):
   result: List[FactAdjudicate]


class AssessOutput(BaseModel):
   requirement_fulfilled: bool
   gap_report: List[str] | None = None


# SYNTHESIS

class SynthesisSection(BaseModel):
   heading: str
   info_ids: List[str]
   content: str
   confidence_flag: Literal["low", "mid", "high"]

class SynthesisOutput(BaseModel):
   subtopic: str
   sections: List[SynthesisSection]


# COMPOSE

class ComposeOutput(BaseModel):
   final_report: str





class VerifiedInfo(BaseModel):
   id: str
   title: str # replace it with keywords query maybe
   sources: list[str] # chunk_ids
   content: str
   trust_score: float
   status: Literal["supported", "contradicted", "unresolved", "uncontested"]

class RecentInfo(BaseModel):
   chunk_id: str
   url: str 
   query: str
   title: str
   content: str


class ControversialFacts(FlaggedFact):
   computed_confidence: float | None
   status: Literal["unresolved"]
   evidence_for: List[EvidenceFor]
   evidence_against: List[EvidenceAgainst]






















# class SaveNotesArgs(BaseModel):
#    key: str
#    content: str
#    source: str

# class ReadNotesArgs(BaseModel):
#    key: str

# class WebSearchArgs(BaseModel):
#    query: str

# class FetchUrlArgs(BaseModel):
#    url: str

# class ToolCall(BaseModel):
#   tool_call_id: str
#   name: str
#   args: Union[WebSearchArgs, FetchUrlArgs, SaveNotesArgs, ReadNotesArgs]

# class ActionSchema(BaseModel):
#   description: str
#   tool_calls: list[ToolCall]

# class ChatOutput(BaseModel):
#   type: Literal["question", "answer"] = "answer"
#   content: str

# class ChatMessage(BaseModel):
#   role: Literal["system", "user", "assistant", "tool"]
#   content: str
#   tool_call_id: str | None = None

# class RecentInformation(BaseModel):
#    content: str
#    source: str

# class contextState(BaseModel):
#     goal: str
#     plan: list[str]
#     current_plan_step: int
#     completed_actions: list[str]
#     recent_info: list[RecentInformation]
#     stored_notes: list[str]
#     status: Literal["planning", "researching", "structuring", "completed", "pending"]

# class LLMOutput(BaseModel):
#   chat_output: Optional[ChatOutput] = None
#   action: Optional[ActionSchema] = None
#   cur_state: contextState



# class State(BaseModel):
#     goal: str
#     plan: list[str]
#     current_plan_step: int
#     completed_actions: list[str]
#     messages: list[ChatMessage]
#     recent_info: list[RecentInformation]
#     stored_notes: list[str]
#     status: Literal["planning", "researching", "structuring", "completed", "pending"]
#     errors: list[str]
#     tool_calls: list[ToolCall]
#     iteration: int

# class Information(BaseModel):
#    source: str
#    content: str
#    time_stamp: str

# class StoredNotes(BaseModel):
#    key: Information

# class ToolResult(BaseModel):
#     tool_call_id: str
#     status: str
#     result: Any




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