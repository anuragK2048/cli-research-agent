Project: Build a Mini Autonomous Research Agent

Build a CLI research agent from scratch in vanilla Python.

The user gives it a task such as:

“Compare the best cloud providers for deploying an AI startup in India, considering cost, GPU availability, and managed services.”

Your agent should independently:

Understand the objective
Break it into subtasks
Decide which tool to use
Execute tools
Inspect results
Decide whether more research is needed
Maintain working memory
Recover from tool failures
Evaluate whether it has enough information
Produce a structured final report

No LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, etc.

Use only Python + standard library + an LLM API.

Phases:
Requirement Gathering
Planning
_plan finalized by user containing multiple sub-topics_ - Researching
_for each plan sub-topic_:
(Phase 1) Data retrieval # Explore all the data # Analyze all the retrieved data # Gather evidence for controversial facts

                (Phase 2) Evaluation
                # Assess the gathered data and controversial facts
                # Find contradictions for controversial facts(retrieve data against claim and then cross examine)
                # Evaluate the real facts
                # Validate the data
                # Save the data in verified_data file which is only source of truth for final report

        (only verified_data would be available from now)
        - Analysing: form the blueprint of report by deciding relevant data and associating it with backed sources
        - Structuring: arrange the data(charts, graphs)

Pipeline
├── Stage 1: Scope
├── Stage 2: Plan
├── Stage 3: Research
│ (for each sub-topic)
│ ├── Phase 1: Retrieval
│ │ ├── Step 1.1 Discover
│ │ ├── Step 1.1.1 Web Search
│ │ ├── Step 1.1.2 URL Fetch
│ │ ├── Step 1.2 Extract
│ │ └── Step 1.3 Flag
│ └── Phase 2: Verification
│   ├── Step 2.1 Corroborate
│   ├── Step 2.2 Challenge
│   ├── Step 2.3 Adjudicate
│   ├── Step 2.4 Assess Coverage (of sub-topic)
│   └── Step 2.5 Commit
├── Stage 4: Synthesize
└── Stage 5: Compose

SCOPE
- ask clarifying questions and establish research requirements
- return chat, status, when status == "completed" -> research_scope: goal, requirements

PLAN
- define sub-topics(with sub-topic checklist) given research_scope
- return plan: [sub-topic: [sub-topic checklist]]

*finalise plan from user*

RESEARCH
given - (sub-topic, topic checklist): requirements
    Phase-1 (Retrieval)

        - Discover
        All raw data acc to requirements

        - Extract (mechanical)
        given - raw data
        form chunks and tag sources
        store it in recent_info [subtopic_id] = [{chunk_id, source, title, content, retrieval_query}]

        - Flag (1 LLM call)
        given - recent_info
        find controversial and uncontested facts 
        store controversial facts in controversial_facts [subtopic_id] = [{fact_id, claim, sources(chunk_id, websites), confidence: None, evidence_for, evidence_against, materiality, status: "unresolved"}]

        directly put uncontested facts in verified_info 
        [dedup, normalize controversial_facts]


    Phase-2 (Verification)
        
        - Corroborate
        (materiality == "high"):
        given - 1 controversial_fact, recent_info
        Make relevant search query (LLM call) -> fetch given web pages (LLM call) ->
        given recent_info and new_info
        Find evidence_for and refer and store the chunks in recent_info(+ search_query)

        (materiality == "medium"):
        given - 5-10(batched) controversial_fact, recent_info
        Make relevant search queries (LLM call) -> fetch given web pages (LLM call) ->
        given recent_info and new_info
        Find evidence_for and refer and store the chunks in recent_info(+ search_query)

        - Challenge (same as Corroborate)

        (calculate return {"verdict": verdict, "confidence": round(confidence, 2), "for_score": for_score, "against_score": against_score}) mechanically for every fact

        - Adjudicate (1 LLM call)
        given fact, evidence_for, evidence_against, confidence 
        give verdict, summary(cite sources also in it), reason, trust_score(based on confidence and LLM reason), stated_reason and store *filtered* facts in verified_info 

        - Assess Coverage
        given requirements, verified_info
        Check if each requirement is fullfilled if yes -> proceed to next stage else(cap - 3 times) prepare a gap_report and proceed to phase-1 with gap_report as requirements

        - Commit verified_info

-------

SYNTHESIS (1 LLM call for each sub-topic)
given verified_info and plan: [sub-topic: [sub-topic checklist]] and research_scope: goal, requirements
input = {
    "subtopic": plan.subtopic_title,
    "subquestions": plan.subquestions,
    "verified_facts": verified_info[subtopic_id]   # list of {key, title, content, sources, trust_score, status}
}
output = {
    "subtopic": "...",
    "sections": [
        {
            "heading": "Revenue Growth",
            "answers_subquestion": "What was Q2 performance?",
            "fact_keys": ["company_x_q2_growth", "company_x_margin_change"],  # pointers, not copied content
            "narrative_note": "1-line note on how these facts connect",           # optional, guides Composition
            "confidence_flag": "low"   # if any included fact has low trust_score, surface it here
        },
        ...
    ],
    "excluded_facts": ["some_key"],   # facts judged irrelevant/redundant — with a reason, for auditability
    "unresolved_gaps": ["..."]           # subquestions with no verified fact addressing them — honest reporting
}

--------

CROSS-TOPIC SYNTHESIS


COMPOSE


ASSEMBLY












tool calls: web_search, fetch_url, save_info



{
    "fact_id": "f_001",
    "claim": "Company X's Q2 revenue grew 40% YoY",
    "source_chunk_ids": ["c_001", "c_004"],   # original chunks that raised this claim
    "materiality": "high" | "low"   # does this fact matter to the final report's conclusions? skip verification for low materiality facts
    "evidence_for": [
        {
            "chunk_id": "c_012",              # new chunk fetched during Corroborate
            "source_url": "...",
            "source_type": "primary",     # primary | official | reputable_news | secondary | blog_forum | unknown
            "published_date": "2026-06-15",
            "supports": "Independent earnings report confirms 40% YoY growth",
            "stance_strength": "direct"        # direct | indirect | partial
        }
    ],

    "evidence_against": [
        {
            "chunk_id": "c_019",              # new chunk fetched during Challenge
            "source_url": "...",
            "contradicts": "Analyst report states growth was 22%, not 40%",
            "source_type": "primary",     # primary | official | reputable_news | secondary | blog_forum | unknown
            "published_date": "2026-06-15",
            "stance_strength": "direct"
        }
    ],

    "status": "unresolved",
    "confidence": None
}


adjudicate
{
    "key": "company_x_q2_growth",
    "verdict": "contradicted",
    "confidence": 0.35,     # from formula
    "summary": "...",         # LLM-written, must cite evidence_for/against
    "trust_score": ...        # possibly = confidence, or further adjusted by Adjudicate with a stated reason
}