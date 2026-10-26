# Research Agent with the OpenAI Agents SDK

This package is the SDK-based implementation of the research pipeline. It keeps
the original implementation available in `agent/` and uses typed agent outputs,
run-scoped tool state, explicit workflow orchestration, and one JSON artifact per
completed run.

## Setup

Gemini is the default provider. Add your Gemini API key to the workspace `.env` file:

```env
GEMINI_API_KEY=...
GEMINI_API_KEY1=...
GEMINI_API_KEY2=...
GEMINI_API_KEY3=...
GEMINI_MODEL=gemini-2.5-flash
```

The base key and numbered keys are loaded in numeric order and used round-robin
for model requests. If a key is rate-limited, over quota, or gets a transient
service/connection error, the request is retried with the remaining keys. Invalid
requests and authentication errors are not retried. Keys belonging to the same
Google Cloud project may share quota, so rotating keys does not necessarily
increase the project's total rate limit.

The default Gemini OpenAI-compatible endpoint is
`https://generativelanguage.googleapis.com/v1beta/openai/`. You can override the
provider with `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. For OpenRouter, for
example, set `LLM_API_KEY`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, and
`LLM_MODEL` to the provider's model ID. `AGENT_MAX_TURNS`, `RESEARCH_MAX_ROUNDS`,
and `RESEARCH_RUNS_DIR` are also optional. The chosen model must support the
structured outputs and tool calling used by this workflow.

Agents SDK tracing is disabled unless a separate `OPENAI_API_KEY` is present;
that key is used only for trace export, not for Gemini model requests. Install
workspace dependencies with `pip install -r requirements.txt`.

## Run

From the repository root:

```bash
python -m openai_agents_sdk "Compare cloud providers for an AI startup in India"
```

If the request is omitted, the CLI prompts for it. Completed runs are saved to
`storage/research_runs/` by default. Search and fetch tools only allow fetching
URLs returned by web search in the active agent run.

While a run is active, live JSON snapshots are written under
`storage/live_state/`: `recent_info.json`, `verified_info.json`, and
`controversial_facts.json`. These three files are reset to empty at the beginning
of each run and updated as research progresses.

## Workflow

1. Scope planner clarifies the request and produces a typed research scope.
2. Planner creates 3-7 independent subtopics with checklists.
3. Discoverer searches and fetches source pages using SDK function tools.
4. Flagging, corroboration, challenge, adjudication, and coverage agents process
   claims and report gaps. Coverage gaps trigger a bounded additional research
   round.
5. Report writer produces a cited report grounded in the collected facts.

Agents do not share mutable global state. A `ResearchContext` is created per run
and passed only to that run's tools.