import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from agents import (
    ModelSettings,
    RunConfig,
    set_default_openai_client,
    set_tracing_export_api_key,
)

set_tracing_export_api_key(os.environ["OPENAI_API_KEY"])
custom_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
set_default_openai_client(custom_client, use_for_tracing=False)
run_config = RunConfig(model_settings=ModelSettings(max_tokens=2048))
