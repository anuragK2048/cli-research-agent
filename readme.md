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
