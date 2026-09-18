def generate_user_prompt(stage, input: dict):
    """Generate the user prompt for LLM in order to give the context and state"""
    try:
        if stage == "plan":
            if "research_scope" in input:
                user_prompt = f"""Given research scope:
                    {input["research_scope"]}
                """
            else:
                print()

        if stage == "discover":
            if "sub_topic" in input:
                user_prompt = f"""Given sub topic and sub questions:
                    {input["sub_topic"]}
                """
            else:
                print()

    except Exception as e:
        print("🔴 Insufficient input provided in generate_user_prompt")
        raise(e)
        
    return user_prompt