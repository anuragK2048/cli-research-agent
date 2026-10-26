from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ResearchScope(BaseModel):
    goal: str
    requirements: list[str] = Field(min_length=1)


class ScopeOutput(BaseModel):
    status: Literal["in-progress", "completed"]
    chat: str | None = None
    research_scope: ResearchScope | None = None


class SubTopic(BaseModel):
    name: str
    check_list: list[str] = Field(min_length=1, max_length=7)


class PlanOutput(BaseModel):
    sub_topics: list[SubTopic] = Field(min_length=3, max_length=7)


class DiscoveryOutput(BaseModel):
    status: Literal["completed"]
    summary: str


class FlaggedFact(BaseModel):
    fact_id: str
    claim: str
    source_chunk_ids: list[str] = Field(min_length=1)
    reason: str
    materiality: Literal["high", "low"] = "low"


class FlagOutput(BaseModel):
    controversial_facts: list[FlaggedFact]


class SupportingEvidence(BaseModel):
    chunk_id: str
    source_type: Literal["primary", "secondary", "unknown"]
    stance_strength: Literal["direct", "indirect", "partial"]
    supports: str


class ContradictingEvidence(BaseModel):
    chunk_id: str
    source_type: Literal["primary", "secondary", "unknown"]
    stance_strength: Literal["direct", "indirect", "partial"]
    contradicts: str


class SupportingEvidenceOutput(BaseModel):
    evidence_for: list[SupportingEvidence]


class ContradictingEvidenceOutput(BaseModel):
    evidence_against: list[ContradictingEvidence]


class FactAdjudication(BaseModel):
    fact_id: str
    verdict: Literal["supported", "contradicted", "unresolved"]
    summary: str
    trust_score: float = Field(ge=0, le=1)
    verdict_reason: str | None = None


class AdjudicationOutput(BaseModel):
    result: list[FactAdjudication]


class CoverageOutput(BaseModel):
    requirement_fulfilled: bool
    gap_report: list[str] | None = None

    @model_validator(mode="after")
    def validate_gap_report(self) -> "CoverageOutput":
        if self.requirement_fulfilled == bool(self.gap_report):
            raise ValueError(
                "Completed coverage must have no gaps; incomplete coverage must list gaps."
            )
        return self


class ReportOutput(BaseModel):
    final_report: str
