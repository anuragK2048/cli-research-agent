from agents import Agent

from prompts.system_prompts import system_prompts

from .models import (
    AdjudicationOutput,
    ContradictingEvidenceOutput,
    CoverageOutput,
    DiscoveryOutput,
    FlagOutput,
    PlanOutput,
    ReportOutput,
    ScopeOutput,
    SupportingEvidenceOutput,
)
from .tools import RESEARCH_TOOLS


def build_agents(model: object) -> dict[str, Agent]:
    tool_policy = (
        "Use the provided tools directly; do not emit JSON tool-call instructions. "
        "Only fetch URLs returned by your own search_web calls."
    )
    discovery_instructions = (
        f"{system_prompts['discover']}\n\n"
        f"{tool_policy} Continue researching until every checklist item has at least "
        "one search and at least two successfully fetched sources per search. "
        "Then return status=completed and a concise summary."
    )
    evidence_tool_policy = (
        f"\n\n{tool_policy} Finish the requested search before returning your "
        "structured evidence list. Cite only chunk_id values returned by fetch_page "
        "during this agent run."
    )

    return {
        "scope": Agent(
            name="Research Scope Planner",
            instructions=system_prompts["scope"],
            model=model,
            output_type=ScopeOutput,
        ),
        "plan": Agent(
            name="Research Planner",
            instructions=system_prompts["plan"],
            model=model,
            output_type=PlanOutput,
        ),
        "discover": Agent(
            name="Research Discoverer",
            instructions=discovery_instructions,
            model=model,
            tools=RESEARCH_TOOLS,
            output_type=DiscoveryOutput,
        ),
        "flag": Agent(
            name="Claim Flagging Analyst",
            instructions=system_prompts["flag"],
            model=model,
            output_type=FlagOutput,
        ),
        "corroborate": Agent(
            name="Claim Corroborator",
            instructions=system_prompts["corroborate.single"] + evidence_tool_policy,
            model=model,
            tools=RESEARCH_TOOLS,
            output_type=SupportingEvidenceOutput,
        ),
        "challenge": Agent(
            name="Claim Challenger",
            instructions=system_prompts["challenge.single"] + evidence_tool_policy,
            model=model,
            tools=RESEARCH_TOOLS,
            output_type=ContradictingEvidenceOutput,
        ),
        "adjudicate": Agent(
            name="Evidence Adjudicator",
            instructions=system_prompts["adjudicate"],
            model=model,
            output_type=AdjudicationOutput,
        ),
        "assess": Agent(
            name="Coverage Assessor",
            instructions=system_prompts["assess"],
            model=model,
            output_type=CoverageOutput,
        ),
        "compose": Agent(
            name="Research Report Writer",
            instructions=(
                system_prompts["compose"]
                + "\n\nFor citations, use the exact `id` values on verified_info "
                "records as fact keys inside [[id]] markers."
            ),
            model=model,
            output_type=ReportOutput,
        ),
    }
