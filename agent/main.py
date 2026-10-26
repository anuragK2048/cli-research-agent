import json
import sys
from pathlib import Path
import uuid

from confidence import compute_confidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.generate_user_prompt import generate_user_prompt
from llms.llm import askLLM
from pydantic_models.models import (
    AdjudicateOutput,
    AssessOutput,
    ChallengeBatchOutput,
    ChallengeSingleOutput,
    ComposeOutput,
    CorroborateSingleOutput,
    DiscoverWebOutput,
    FlagOutput,
    PlanOutput,
    ScopeOutput,
    CorroborateBatchOutput,
)
from agent.handleLLMoutput import processOutput
from agent.state import (
    add_to_verified_info,
    get_controversial_facts,
    get_recent_info,
    get_verified_info,
    reset_controversial_facts,
    reset_recent_info,
    update_cur_state,
)
from agent.state import get_cur_state
from prompts.system_prompts import system_prompts

with open(f"memory/controversial_facts.json", "w") as f:
    json.dump([], f, indent=2, ensure_ascii=False)
with open(f"memory/recent_info.json", "w") as f:
    json.dump([], f, indent=2, ensure_ascii=False)
with open(f"memory/verified_info.json", "w") as f:
    json.dump([], f, indent=2, ensure_ascii=False)
with open(f"llms/debug/llm_output.json", "w") as f:
    json.dump([], f, indent=2, ensure_ascii=False)
with open(f"llms/debug/messages.json", "w") as f:
    json.dump([], f, indent=2, ensure_ascii=False)


llm_stages_config = {
    "scope": {
        "system_prompt": system_prompts["scope"],
        "context_inputs": "",
        "output_schema": ScopeOutput,
    },
    "plan": {
        "system_prompt": system_prompts["plan"],
        "context_inputs": "research_scope",
        "output_schema": PlanOutput,
    },
    "discover": {
        "system_prompt": system_prompts["discover"],
        "context_inputs": "sub_topic",
        "output_schema": DiscoverWebOutput,
    },
    "flag": {
        "system_prompt": system_prompts["flag"],
        "context_inputs": "sub_topic, recent_info",
        "output_schema": FlagOutput,
    },
    "corroborate.single": {
        "system_prompt": system_prompts["corroborate.single"],
        "context_inputs": "controversial_fact, recent_info[fact.source_chunk_id]",
        "output_schema": CorroborateSingleOutput,
    },
    "corroborate.batched": {
        "system_prompt": system_prompts["corroborate.batched"],
        "context_inputs": "controversial_facts, recent_info[facts.source_chunk_ids]",
        "output_schema": CorroborateBatchOutput,
    },
    "challenge.single": {
        "system_prompt": system_prompts["challenge.single"],
        "context_inputs": "controversial_fact, recent_info[fact.source_chunk_id]",
        "output_schema": ChallengeSingleOutput,
    },
    "challenge.batched": {
        "system_prompt": system_prompts["challenge.batched"],
        "context_inputs": "controversial_facts, recent_info[facts.source_chunk_ids]",
        "output_schema": ChallengeBatchOutput,
    },
    "adjudicate": {
        "system_prompt": system_prompts["adjudicate"],
        "context_inputs": "controversial_facts",
        "output_schema": AdjudicateOutput,
    },
    "assess": {
        "system_prompt": system_prompts["assess"],
        "context_inputs": "sub_topic, verified_info",
        "output_schema": AssessOutput,
    },
    # "synthesis": {
    #     "system_prompt": system_prompts["synthesis"],
    #     "context_inputs": "sub_topic, verified_info",
    #     "output_schema":
    # },
    "compose": {
        "system_prompt": system_prompts["compose"],
        "context_inputs": "research_scope, sub_topic, verified_info",
        "output_schema": ComposeOutput,
    },
}


askLLMConfig = {
    "llms": ["gemini", "cloudOllama"],
    "retries": 3,
}


messages = []
messages.append(
    {"role": "system", "content": llm_stages_config["scope"]["system_prompt"]}
)

# scope
while True:
    user_input = input("> ")
    # user_input = "Compare the best cloud providers for deploying an AI startup in India, considering cost, GPU availability, and managed services."
    messages.append({"role": "user", "content": user_input})
    output = askLLM(messages, llm_stages_config["scope"]["output_schema"])
    if output["chat"] is not None:
        print(">> ", output["chat"])
        messages.append({"role": "assistant", "content": output["chat"]})
    if output["status"] == "completed":
        processOutput("scope", output)
        # plan
        messages = []
        messages.append(
            {"role": "system", "content": llm_stages_config["plan"]["system_prompt"]}
        )
        messages.append(
            {
                "role": "user",
                "content": generate_user_prompt(
                    "plan", {"research_scope": get_cur_state()["research_scope"]}
                ),
            }
        )
        output = askLLM(messages, llm_stages_config["plan"]["output_schema"])
        print(json.dumps(output["sub_topics"], indent=2))
        # print("Confirm this plan?")
        # user_input = input('>>>>> "Yes" or "No"')
        # if user_input == "No":
        #     messages.append({"role": "assistant", "content": output})
        #     messages.append({"role": "user", "content": "I want change in the current plan. Do requirement gathering again"})
        #     print("> What else do you want?")
        # if user_input == "Yes":
        if True:
            processOutput("plan", output)

            # research stage
            for sub_topic in get_cur_state()["sub_topics"]:
                print(f">> PROGRESS: cur_subtopic: {sub_topic}")
                reset_recent_info()
                reset_controversial_facts()
                # discover
                print(">> PROGRESS: discover")
                messages = []
                messages.append(
                    {
                        "role": "system",
                        "content": llm_stages_config["discover"]["system_prompt"],
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": generate_user_prompt(
                            "discover", {"sub_topic": sub_topic}
                        ),
                    }
                )
                output = askLLM(
                    messages, llm_stages_config["discover"]["output_schema"]
                )
                while output["status"] != "completed":
                    result = processOutput("discover", output)
                    messages.append({"role": "user", "content": json.dumps(result)})
                    output = askLLM(
                        messages, llm_stages_config["discover"]["output_schema"]
                    )

                # flag
                print(">> PROGRESS: flag")
                messages = []
                recent_info = get_recent_info()
                messages.append(
                    {
                        "role": "system",
                        "content": llm_stages_config["flag"]["system_prompt"],
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": generate_user_prompt(
                            "flag", {"sub_topic": sub_topic, "recent_info": recent_info}
                        ),
                    }
                )
                output = askLLM(messages, llm_stages_config["flag"]["output_schema"])
                result = processOutput("flag", output)

                # corroborate
                print(">> PROGRESS: corroborate")
                all_controversial_facts = get_controversial_facts()
                recent_info = get_recent_info()
                # region Process controversial facts
                high_materiality_facts = []
                low_materiality_facts_batches = []
                max_batch_size = 8
                size = 0
                cur_batch = []
                for fact in all_controversial_facts:
                    if fact["materiality"] == "high":
                        high_materiality_facts.append(fact)
                    else:
                        if size < max_batch_size:
                            cur_batch.append(fact)
                            size += 1
                        else:
                            low_materiality_facts_batches.append(cur_batch)
                            cur_batch = [fact]
                            size = 1

                if cur_batch:
                    low_materiality_facts_batches.append(cur_batch)
                # endregion

                # def handleCorroborateAndChallenge(type: str, ):

                # handleCorroborateAndChallenge("corroborate")
                # handleCorroborateAndChallenge("challenge")

                for fact in high_materiality_facts:
                    messages = []
                    discovered_chunks = []
                    messages.append(
                        {
                            "role": "system",
                            "content": llm_stages_config["corroborate.single"][
                                "system_prompt"
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": generate_user_prompt(
                                "corroborate.single",
                                {
                                    "controversial_fact": fact,
                                    "recent_info": recent_info,
                                },
                            ),
                        }
                    )
                    output = askLLM(
                        messages,
                        llm_stages_config["corroborate.single"]["output_schema"],
                    )
                    while output.get("tool_calls"):
                        output["fact_id"] = fact["fact_id"]
                        output["discovered_chunks"] = discovered_chunks
                        result = processOutput("corroborate.single", output)
                        messages.append({"role": "user", "content": json.dumps(result)})
                        output = askLLM(
                            messages,
                            llm_stages_config["corroborate.single"]["output_schema"],
                        )
                    output["fact_id"] = fact["fact_id"]
                    output["discovered_chunks"] = discovered_chunks
                    processOutput("corroborate.single", output)

                for batch in low_materiality_facts_batches:
                    messages = []
                    discovered_chunks = []
                    messages.append(
                        {
                            "role": "system",
                            "content": llm_stages_config["corroborate.batched"][
                                "system_prompt"
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": generate_user_prompt(
                                "corroborate.batched",
                                {
                                    "controversial_facts": batch,
                                    "recent_info": recent_info,
                                },
                            ),
                        }
                    )
                    output = askLLM(
                        messages,
                        llm_stages_config["corroborate.batched"]["output_schema"],
                    )
                    while output.get("tool_calls"):
                        output["discovered_chunks"] = discovered_chunks
                        result = processOutput("corroborate.batched", output)
                        messages.append({"role": "user", "content": json.dumps(result)})
                        output = askLLM(
                            messages,
                            llm_stages_config["corroborate.batched"]["output_schema"],
                        )
                    output["discovered_chunks"] = discovered_chunks
                    processOutput("corroborate.batched", output)

                # challenge
                print(">> PROGRESS: challenge")
                for fact in high_materiality_facts:
                    messages = []
                    discovered_chunks = []
                    messages.append(
                        {
                            "role": "system",
                            "content": llm_stages_config["challenge.single"][
                                "system_prompt"
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": generate_user_prompt(
                                "challenge.single",
                                {
                                    "controversial_fact": fact,
                                    "recent_info": recent_info,
                                },
                            ),
                        }
                    )
                    output = askLLM(
                        messages, llm_stages_config["challenge.single"]["output_schema"]
                    )
                    while output.get("tool_calls"):
                        output["fact_id"] = fact["fact_id"]
                        output["discovered_chunks"] = discovered_chunks
                        result = processOutput("challenge.single", output)
                        messages.append({"role": "user", "content": json.dumps(result)})
                        output = askLLM(
                            messages,
                            llm_stages_config["challenge.single"]["output_schema"],
                        )
                    output["fact_id"] = fact["fact_id"]
                    output["discovered_chunks"] = discovered_chunks
                    processOutput("challenge.single", output)

                for batch in low_materiality_facts_batches:
                    messages = []
                    discovered_chunks = []
                    messages.append(
                        {
                            "role": "system",
                            "content": llm_stages_config["challenge.batched"][
                                "system_prompt"
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": generate_user_prompt(
                                "challenge.batched",
                                {
                                    "controversial_facts": batch,
                                    "recent_info": recent_info,
                                },
                            ),
                        }
                    )
                    output = askLLM(
                        messages,
                        llm_stages_config["challenge.batched"]["output_schema"],
                    )
                    while output.get("tool_calls"):
                        output["discovered_chunks"] = discovered_chunks
                        result = processOutput("challenge.batched", output)
                        messages.append({"role": "user", "content": json.dumps(result)})
                        output = askLLM(
                            messages,
                            llm_stages_config["challenge.batched"]["output_schema"],
                        )
                    output["discovered_chunks"] = discovered_chunks
                    processOutput("challenge.batched", output)

                # Calculate confidence for each controversial_fact
                for fact in get_controversial_facts():
                    result = compute_confidence(
                        fact["evidence_for"], fact["evidence_against"]
                    )
                    fact["computed_confidence"] = result["confidence"]

                # Adjudicate
                print(">> PROGRESS: adjudicate")
                messages = []
                messages.append(
                    {
                        "role": "system",
                        "content": llm_stages_config["adjudicate"]["system_prompt"],
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": generate_user_prompt(
                            "adjudicate",
                            {"controversial_facts": get_controversial_facts()},
                        ),
                    }
                )
                output = askLLM(
                    messages, llm_stages_config["adjudicate"]["output_schema"]
                )
                result = processOutput("adjudicate", output)

                # commit facts to verified_info
                verified_facts = []
                controversial_facts = get_controversial_facts()
                recent_info = get_recent_info()

                for fact in controversial_facts:
                    verified = {
                        "id": str(uuid.uuid4()),
                        "title": fact["claim"],
                        "sources": fact["source_chunk_ids"],
                        "content": fact["summary"],
                        "trust_score": fact["trust_score"],
                        "status": fact["verdict"],
                    }
                    verified_facts.append(verified)

                add_to_verified_info(verified_facts)

                # Assess
                print(">> PROGRESS: assess")
                messages = []
                messages.append(
                    {
                        "role": "system",
                        "content": llm_stages_config["assess"]["system_prompt"],
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": generate_user_prompt(
                            "assess",
                            {
                                "sub_topic": sub_topic,
                                "verified_info": get_verified_info(),
                            },
                        ),
                    }
                )
                output = askLLM(messages, llm_stages_config["assess"]["output_schema"])
                result = processOutput("assess", output)

            # Synthesize

            # Compose
            print(">> PROGRESS: compose")
            messages = []
            messages.append(
                {
                    "role": "system",
                    "content": llm_stages_config["compose"]["system_prompt"],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": generate_user_prompt(
                        "compose",
                        {
                            "sub_topics": get_cur_state()["sub_topics"],
                            "verified_info": get_verified_info(),
                            "research_scope": get_cur_state()["research_scope"],
                        },
                    ),
                }
            )
            output = askLLM(messages, llm_stages_config["compose"]["output_schema"])
            print(output["final_report"])

    print("DONEEEEEE")
    break
