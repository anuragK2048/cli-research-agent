def generate_user_prompt(stage, input: dict):
    """Generate the user prompt for LLM in order to give the context and state"""
    try:
        if stage == "plan":
            if "research_scope" in input:
                user_prompt = f"""Given research scope:
                    {input["research_scope"]}
                """
            else:
                print("----- Insufficient input in generate_user_prompt")

        if stage == "discover":
            if "sub_topic" in input:
                user_prompt = f"""Given sub topic and sub questions:
                    {input["sub_topic"]}
                """
            else:
                print("----- Insufficient input in generate_user_prompt")

        if stage == "flag":
            if "sub_topic" in input and "recent_info" in input:
                sub_topic, recent_info = input["sub_topic"], input["recent_info"]
                user_prompt = f"""Given sub topic and sub questions:
                    {sub_topic},
                    Given recent_info
                    {recent_info}
                """
            else:
                print("----- Insufficient input in generate_user_prompt")

        if stage == "corroborate.single" or stage == "challenge.single":
            if "controversial_fact" in input and "recent_info" in input:
                controversial_fact, recent_info = input["controversial_fact"], input["recent_info"]
                relevant_recent_info = []
                for chunk in recent_info:
                    if chunk["chunk_id"] in controversial_fact["source_chunk_ids"]:
                        relevant_recent_info.append(chunk)
                user_prompt = f"""Given controversial claim:
                    {controversial_fact},
                    Given related chunks
                    {relevant_recent_info}
                """
            else:
                print("----- Insufficient input in generate_user_prompt")

        if stage == "corroborate.batched" or stage == "challenge.batched":
            if "controversial_facts" in input and "recent_info" in input:
                controversial_facts, recent_info = input["controversial_facts"], input["recent_info"]
                relevant_recent_info = []
                for chunk in recent_info:
                    if any(chunk["chunk_id"] in fact["source_chunk_ids"] for fact in controversial_facts):
                        relevant_recent_info.append(chunk)
                user_prompt = f"""Given list of controversial claims:
                    {controversial_facts},
                    Given related chunks
                    {relevant_recent_info}
                """
            else:
                print("----- Insufficient input in generate_user_prompt")

        if stage == "adjudicate":
            if "controversial_facts" in input:
                controversial_facts = input["controversial_facts"]
                formatted_facts = []
                for fact in controversial_facts:
                    formatted_facts.append({
                        "fact_id": fact["fact_id"],
                        "claim": fact["claim"],
                        "evidence_for": fact["evidence_for"],
                        "evidence_against": fact["evidence_against"],
                        "computed_confidence": fact["computed_confidence"]
                    })
                user_prompt = f"""Given list of disputed facts:
                    {controversial_facts}
                """

        if stage == "assess":
            if "sub_topic" in input and "verified_info" in input:
                user_prompt = f"""Given subtopic and requirement checklist:
                    {input["sub_topic"]},
                    Information gathered:
                    {input["verified_info"]}
                """

        if stage == "compose":
            if "sub_topics" in input and "verified_info" in input and "research_scope" in input:
                user_prompt = f"""Given research scope:
                    {input["research_scope"]},
                    Sub topics:
                    {input["sub_topics"]},
                    Verified info:
                    {input["verified_info"]}
                """

    except Exception as e:
        print("🔴 Insufficient input provided in generate_user_prompt")
        raise(e)
        
    return user_prompt