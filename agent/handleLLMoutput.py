import json
import uuid
from agent.state import add_to_controversial_facts, add_to_verified_info, get_controversial_facts, get_recent_info, update_cur_state, add_to_recent_info
from tools.web_search import web_search
from tools.fetch_url import fetch_url
from tools.notes import save_info, read_info

tool_registry = {
    "web_search": {
        "function": web_search,
        "description": "Search the web for information",
        "parameters": {
            "query": "string"
        }
    },
    "fetch_url": {
        "function": fetch_url,
        "description": "Fetch content from a url",
        "parameters": {
            "url": "string"
        }
    },
}

def processOutput(stage, LLM_output):

    if stage == "scope":
        if LLM_output.get("research_scope"):
            update_cur_state({"research_scope": LLM_output["research_scope"]})
        else:
            raise

    if stage == "plan":
        if LLM_output.get("sub_topics"):
            update_cur_state({"sub_topics": LLM_output["sub_topics"]})
        else:
            raise

    if stage == "discover":
        if LLM_output.get("tool_calls"):
            tool_calls_output = []
            new_recent_infos = []
            # print(LLM_output)
            tool_calls = LLM_output["tool_calls"]
            for use_tool in tool_calls:
                # update_tool_call_history([use_tool["name"], use_tool["args"]])
                tool = tool_registry[use_tool["name"]]
                output = tool["function"](**use_tool["args"])
                # save chunks in recent_info
                # extract
                if use_tool["name"] == "fetch_url":
                    new_recent_infos.extend(output["result"])
                    tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": "saved top relevant chunks from this webpage"})
                else:
                    tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": output})
            add_to_recent_info(new_recent_infos)

            return {"tool_call_result": tool_calls_output}
        
    if stage == "flag":
        if LLM_output.get("controversial_facts"):
            controversial_facts = LLM_output["controversial_facts"]
            controversial_chunk_ids = []
            full_controversial_facts = []
            for fact in controversial_facts:
                full_fact = {**fact, "computed_confidence": None, "status": "unresolved", "evidence_for": [], "evidence_against": []}
                full_controversial_facts.append(full_fact)
                controversial_chunk_ids.extend([chunk_id for chunk_id in fact["source_chunk_ids"]])

            add_to_controversial_facts(full_controversial_facts)

            # move uncontroversial chunks to verified_info
            new_verified_infos = []
            recent_info = get_recent_info()
            for info in recent_info:
                if info["chunk_id"] not in controversial_chunk_ids:
                    verified_info = {
                        "id": str(uuid.uuid4()),
                        "title": info["title"],
                        "sources": [info["url"]],
                        "content": info["content"],
                        "trust_score": 1.0,
                        "status": "uncontested"
                    }
                    new_verified_infos.append(verified_info)

            add_to_verified_info(new_verified_infos)

            return {"result": "added controversial facts and recent_info successfully"}


    if stage == "corroborate.single" or stage == "challenge.single":
        evidence = ""
        if stage == "corroborate.single":
            evidence = "evidence_for"
        else:
            evidence = "evidence_against"
        if LLM_output.get("tool_calls"):
            discovered_chunks = LLM_output["discovered_chunks"]
            tool_calls_output = []
            tool_calls = LLM_output["tool_calls"]
            for use_tool in tool_calls:
                tool = tool_registry[use_tool["name"]]
                output = tool["function"](**use_tool["args"])
                if use_tool["name"] == "fetch_url":
                    discovered_chunks.extend(output["result"])
                    tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": "saved top relevant chunks from this webpage"})
                else:
                    tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": output})

            return {"tool_call_result": tool_calls_output}


        if LLM_output.get(evidence):
            # extending evidence of a controversial_fact
            fact_id = LLM_output["fact_id"]
            for fact in get_controversial_facts():
                if fact["fact_id"] == fact_id:
                    fact[evidence].extend(LLM_output[evidence])
                    break

            from agent.state import log
            log(get_controversial_facts(), "controversial_facts")

            # storing new referenced chunks in recent_info
            new_chunk_ids = [evidence["chunk_id"] for evidence in LLM_output[evidence]]
            discovered_chunks = LLM_output["discovered_chunks"]
            used_chunks = [chunk for chunk in discovered_chunks if chunk["chunk_id"] in new_chunk_ids]
            add_to_recent_info(used_chunks)

            return {"result": "successfully added evidence to fact and new chunks in recent_info"}
        
    if stage == "corroborate.batched" or stage == "challenge.batched":
        if stage == "corroborate.batched":
            evidence = "evidence_for"
        else:
            evidence = "evidence_against"
        if LLM_output.get("tool_calls"):
            discovered_chunks = LLM_output["discovered_chunks"]
            tool_calls_output = []
            tool_calls = LLM_output["tool_calls"]
            for use_tool in tool_calls:
                tool = tool_registry[use_tool["name"]]
                output = tool["function"](**use_tool["args"])
                if use_tool["name"] == "fetch_url":
                    discovered_chunks.extend(output["result"])
                    tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": "saved top relevant chunks from this webpage"})
                tool_calls_output.append({"tool_call_id": use_tool["id"], "status": "success", "result": output})

            return {"tool_call_result": tool_calls_output}


        if LLM_output.get("result"):
            # extending evidence of included controversial facts
            result = LLM_output["result"]
            for el in result:
                fact_id = el["fact_id"]
                for fact in get_controversial_facts():
                    if fact["fact_id"] == fact_id:
                        fact[evidence].extend(el[evidence])
                        break

            from agent.state import log
            log(get_controversial_facts(), "controversial_facts")

            # storing new referenced chunks in recent_info
            for el in result:
                new_chunk_ids = [evidence["chunk_id"] for evidence in el[evidence]]
                discovered_chunks = LLM_output["discovered_chunks"]
                used_chunks = [chunk for chunk in discovered_chunks if chunk["chunk_id"] in new_chunk_ids]
                add_to_recent_info(used_chunks)

            return {"result": "successfully added batched evidences to facts and new chunks in recent_info"}


    if stage == "adjudicate":
        if LLM_output.get("result"):
            controversial_facts = get_controversial_facts()
            for fact in LLM_output["result"]:
                selected_fact = next(
                    (el for el in controversial_facts if el["fact_id"] == fact["fact_id"]),
                    None
                )

                if selected_fact:
                    selected_fact.update(fact)

            return {"result": "updated controversial_facts with adjudicate results"}
    

    if stage == "assess":
        if LLM_output.get("requirement_fulfilled"):
            if LLM_output.get("requirement_fulfilled") == False:
                print(f"👹😓 requirement not fullfiled, gap-report: {LLM_output["gap_report"]}")