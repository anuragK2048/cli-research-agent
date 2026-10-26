import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import (
    RunConfig,
    Runner,
    ToolExecutionConfig,
    set_tracing_export_api_key,
)
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .agents import build_agents
from .context import ResearchContext
from .live_state import LiveStateStore
from .models import (
    AdjudicationOutput,
    ContradictingEvidenceOutput,
    CoverageOutput,
    FlagOutput,
    PlanOutput,
    ReportOutput,
    ScopeOutput,
    SupportingEvidenceOutput,
)
from .model_fallback import RotatingFallbackModel
from .scoring import compute_confidence
from .settings import Settings

ProgressCallback = Callable[[str], None]
ClarificationCallback = Callable[[str], str]


def run_research(
    request: str,
    settings: Settings,
    *,
    clarification_provider: ClarificationCallback | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run a complete research pipeline and save a JSON artifact."""
    if not request.strip():
        raise ValueError("Research request must not be empty.")

    live_state = LiveStateStore(settings.runs_dir.parent / "live_state")
    live_state.clear()
    model = _create_provider_model(settings)
    tracing_api_key = os.getenv("OPENAI_API_KEY")
    if tracing_api_key:
        set_tracing_export_api_key(tracing_api_key)
    run_config = _create_run_config(model, tracing_disabled=not tracing_api_key)
    agents = build_agents(model)
    context = ResearchContext(recent_info_observer=live_state.write_recent_info)
    notify = progress or logging.getLogger(__name__).debug
    notify(f"Live state snapshots: {live_state.directory}")

    scope = _get_scope(
        agents["scope"],
        request,
        context,
        settings,
        run_config,
        clarification_provider,
    )
    notify("Planning research topics")
    plan_result = _run(
        agents["plan"],
        _to_json({"research_scope": scope.model_dump()}),
        context,
        settings,
        run_config,
    )
    plan = _expect_output(plan_result, PlanOutput)

    verified_info: list[dict[str, Any]] = []
    coverage_results: list[dict[str, Any]] = []
    for topic_index, topic in enumerate(plan.sub_topics, start=1):
        notify(f"Researching topic {topic_index}/{len(plan.sub_topics)}: {topic.name}")
        topic_info, coverage = _research_topic(
            topic.model_dump(),
            topic_index,
            agents,
            context,
            live_state,
            verified_info,
            settings,
            run_config,
            notify,
        )
        verified_info.extend(topic_info)
        live_state.write_verified_info(verified_info)
        coverage_results.append({"sub_topic": topic.name, **coverage.model_dump()})

    notify("Writing the final report")
    report_result = _run(
        agents["compose"],
        _to_json(
            {
                "research_scope": scope.model_dump(),
                "sub_topics": [topic.model_dump() for topic in plan.sub_topics],
                "verified_info": verified_info,
                "coverage_results": coverage_results,
            }
        ),
        context,
        settings,
        run_config,
    )
    report = _expect_output(report_result, ReportOutput)

    run_id = uuid.uuid4().hex
    artifact = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.model_name,
        "research_scope": scope.model_dump(),
        "sub_topics": [topic.model_dump() for topic in plan.sub_topics],
        "coverage": coverage_results,
        "verified_info": verified_info,
        "final_report": report.final_report,
    }
    artifact_path = _save_artifact(settings.runs_dir, run_id, artifact)
    return {**artifact, "artifact_path": str(artifact_path)}


def _get_scope(
    agent: Any,
    request: str,
    context: ResearchContext,
    settings: Settings,
    run_config: RunConfig,
    clarification_provider: ClarificationCallback | None,
) -> ScopeOutput:
    transcript = [f"User research request: {request}"]
    for _ in range(10):
        result = _run(
            agent,
            "\n\n".join(transcript),
            context,
            settings,
            run_config,
        )
        scope_result = _expect_output(result, ScopeOutput)
        if scope_result.status == "completed" and scope_result.research_scope:
            return scope_result

        if not scope_result.chat:
            raise RuntimeError(
                "Scope agent requested clarification without a question."
            )
        if clarification_provider is None:
            raise RuntimeError(
                f"More detail is needed before research can start: {scope_result.chat}"
            )
        transcript.append(f"Assistant clarification: {scope_result.chat}")
        transcript.append(
            f"User clarification: {clarification_provider(scope_result.chat)}"
        )

    raise RuntimeError("Research scope was not resolved after 10 clarification turns.")


def _research_topic(
    topic: dict[str, Any],
    topic_index: int,
    agents: dict[str, Any],
    context: ResearchContext,
    live_state: LiveStateStore,
    previously_verified: list[dict[str, Any]],
    settings: Settings,
    run_config: RunConfig,
    progress: ProgressCallback,
) -> tuple[list[dict[str, Any]], CoverageOutput]:
    topic_info: list[dict[str, Any]] = []
    additional_questions: list[str] = []
    coverage = CoverageOutput(
        requirement_fulfilled=False, gap_report=topic["check_list"]
    )

    for round_index in range(settings.max_research_rounds):
        context.clear_recent_info()
        context.start_tool_session()
        prompt_data = {
            "sub_topic": topic,
            "additional_questions": additional_questions,
            "research_round": round_index + 1,
        }
        progress(f"  Discovering sources (round {round_index + 1})")
        _run(
            agents["discover"],
            _to_json(prompt_data),
            context,
            settings,
            run_config,
        )
        topic_chunks = list(context.recent_info)

        progress("  Flagging disputed claims")
        flag_result = _run(
            agents["flag"],
            _to_json({"sub_topic": topic, "recent_info": topic_chunks}),
            context,
            settings,
            run_config,
        )
        flagged = _expect_output(flag_result, FlagOutput).controversial_facts
        valid_chunk_ids = {chunk.get("chunk_id") for chunk in topic_chunks}
        flagged = [
            fact.model_copy(
                update={
                    "fact_id": _stable_fact_id(topic_index, topic["name"], fact.claim)
                }
            )
            for fact in flagged
            if any(chunk_id in valid_chunk_ids for chunk_id in fact.source_chunk_ids)
        ]
        unique_flagged = {fact.fact_id: fact for fact in flagged}
        flagged = list(unique_flagged.values())
        live_state.add_controversial_facts(
            [
                {
                    **fact.model_dump(),
                    "computed_confidence": None,
                    "status": "unresolved",
                    "evidence_for": [],
                    "evidence_against": [],
                }
                for fact in flagged
            ]
        )
        disputed_chunk_ids = {
            chunk_id
            for fact in flagged
            for chunk_id in fact.source_chunk_ids
            if chunk_id in valid_chunk_ids
        }
        topic_info.extend(
            _uncontested_facts(topic_chunks, disputed_chunk_ids, topic_info)
        )
        live_state.write_verified_info([*previously_verified, *topic_info])

        previously_processed = {
            item["id"] for item in topic_info if item["status"] != "uncontested"
        }
        new_flags = [
            fact for fact in flagged if fact.fact_id not in previously_processed
        ]
        disputed_facts = _collect_evidence(
            new_flags,
            topic_chunks,
            agents,
            context,
            settings,
            run_config,
            progress,
        )
        live_state.update_controversial_facts(disputed_facts)
        if disputed_facts:
            progress("  Adjudicating evidence")
            adjudication_result = _run(
                agents["adjudicate"],
                _to_json({"controversial_facts": disputed_facts}),
                context,
                settings,
                run_config,
            )
            adjudications = _expect_output(adjudication_result, AdjudicationOutput)
            live_state.update_controversial_facts(
                _attach_adjudications(disputed_facts, adjudications)
            )
            topic_info.extend(_verified_disputed_facts(disputed_facts, adjudications))
            live_state.write_verified_info([*previously_verified, *topic_info])

        progress("  Assessing checklist coverage")
        coverage_result = _run(
            agents["assess"],
            _to_json({"sub_topic": topic, "verified_info": topic_info}),
            context,
            settings,
            run_config,
        )
        coverage = _expect_output(coverage_result, CoverageOutput)
        if coverage.requirement_fulfilled:
            break
        additional_questions = coverage.gap_report or topic["check_list"]

    return topic_info, coverage


def _collect_evidence(
    flagged: list[Any],
    topic_chunks: list[dict[str, Any]],
    agents: dict[str, Any],
    context: ResearchContext,
    settings: Settings,
    run_config: RunConfig,
    progress: ProgressCallback,
) -> list[dict[str, Any]]:
    known_chunk_ids = {chunk.get("chunk_id") for chunk in topic_chunks}
    collected: list[dict[str, Any]] = []

    for fact in flagged:
        origin_chunks = [
            chunk
            for chunk in topic_chunks
            if chunk.get("chunk_id") in fact.source_chunk_ids
        ]
        progress(f"  Verifying claim: {fact.claim[:90]}")

        context.start_tool_session()
        first_new_chunk = len(context.recent_info)
        support_result = _run(
            agents["corroborate"],
            _to_json(
                {
                    "controversial_fact": fact.model_dump(),
                    "origin_chunks": origin_chunks,
                }
            ),
            context,
            settings,
            run_config,
        )
        support = _expect_output(support_result, SupportingEvidenceOutput)
        support_chunks = {
            chunk.get("chunk_id") for chunk in context.recent_info[first_new_chunk:]
        }
        evidence_for = [
            item.model_dump()
            for item in support.evidence_for
            if item.chunk_id in support_chunks and item.chunk_id not in known_chunk_ids
        ]

        context.start_tool_session()
        first_new_chunk = len(context.recent_info)
        challenge_result = _run(
            agents["challenge"],
            _to_json(
                {
                    "controversial_fact": fact.model_dump(),
                    "origin_chunks": origin_chunks,
                }
            ),
            context,
            settings,
            run_config,
        )
        challenge = _expect_output(challenge_result, ContradictingEvidenceOutput)
        challenge_chunks = {
            chunk.get("chunk_id") for chunk in context.recent_info[first_new_chunk:]
        }
        evidence_against = [
            item.model_dump()
            for item in challenge.evidence_against
            if item.chunk_id in challenge_chunks
            and item.chunk_id not in known_chunk_ids
        ]
        confidence = compute_confidence(evidence_for, evidence_against)
        collected.append(
            {
                **fact.model_dump(),
                "evidence_for": evidence_for,
                "evidence_against": evidence_against,
                "computed_confidence": confidence,
            }
        )

    return collected


def _uncontested_facts(
    chunks: list[dict[str, Any]],
    disputed_chunk_ids: set[str],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {item["id"] for item in existing}
    facts = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if not chunk_id or chunk_id in disputed_chunk_ids or chunk_id in existing_ids:
            continue
        facts.append(
            {
                "id": chunk_id,
                "title": chunk.get("title", "Research source"),
                "sources": [chunk.get("url", "")],
                "content": chunk.get("content", ""),
                "trust_score": 1.0,
                "status": "uncontested",
            }
        )
        existing_ids.add(chunk_id)
    return facts


def _verified_disputed_facts(
    facts: list[dict[str, Any]], adjudications: AdjudicationOutput
) -> list[dict[str, Any]]:
    adjudication_by_id = {
        adjudication.fact_id: adjudication for adjudication in adjudications.result
    }
    verified = []
    for source_fact in facts:
        adjudication = adjudication_by_id.get(source_fact["fact_id"])
        if adjudication is None:
            status = "unresolved"
            summary = (
                "The claim could not be fully adjudicated from the available evidence."
            )
            trust_score = 0.0
        else:
            status = adjudication.verdict
            summary = adjudication.summary
            trust_score = adjudication.trust_score
        verified.append(
            {
                "id": source_fact["fact_id"],
                "title": source_fact["claim"],
                "sources": source_fact["source_chunk_ids"],
                "content": summary,
                "trust_score": trust_score,
                "status": status,
            }
        )
    return verified


def _attach_adjudications(
    facts: list[dict[str, Any]], adjudications: AdjudicationOutput
) -> list[dict[str, Any]]:
    by_id = {item.fact_id: item.model_dump() for item in adjudications.result}
    return [
        {
            **fact,
            **by_id[fact["fact_id"]],
            "status": by_id[fact["fact_id"]]["verdict"],
        }
        for fact in facts
        if fact["fact_id"] in by_id
    ]


def _stable_fact_id(topic_index: int, topic_name: str, claim: str) -> str:
    identity = (
        f"{topic_index}:{topic_name.casefold()}:{' '.join(claim.casefold().split())}"
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"fact-{digest}"


def _run(
    agent: Any,
    prompt: str,
    context: ResearchContext,
    settings: Settings,
    run_config: RunConfig,
) -> Any:
    return Runner.run_sync(
        agent,
        prompt,
        context=context,
        max_turns=settings.max_agent_turns,
        run_config=run_config,
    ).final_output


def _create_run_config(model: Any, *, tracing_disabled: bool = True) -> RunConfig:
    return RunConfig(
        model=model,
        # model_settings=ModelSettings(max_tokens=8000),
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=5),
        tracing_disabled=tracing_disabled,
        trace_include_sensitive_data=True,
        workflow_name="Research Agent",
    )


def _create_provider_model(settings: Settings) -> RotatingFallbackModel:
    models = []
    for api_key in settings.api_keys:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.base_url,
            max_retries=0,
        )
        models.append(
            OpenAIChatCompletionsModel(
                model=settings.model_name,
                openai_client=client,
            )
        )
    return RotatingFallbackModel(models)


def _expect_output(output: Any, output_type: type[Any]) -> Any:
    if not isinstance(output, output_type):
        raise TypeError(
            f"Expected {output_type.__name__} from agent, got {type(output).__name__}."
        )
    return output


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def _save_artifact(runs_dir: Path, run_id: str, artifact: dict[str, Any]) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = runs_dir / f"{run_id}.json"
    temporary_path = artifact_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(artifact_path)
    return artifact_path
