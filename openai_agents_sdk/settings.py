from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_keys: tuple[str, ...]
    base_url: str
    model_name: str
    runs_dir: Path
    max_agent_turns: int = 30
    max_research_rounds: int = 2


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    generic_api_key = os.getenv("LLM_API_KEY")
    gemini_api_keys = _get_gemini_api_keys()
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    configured_base_url = os.getenv("LLM_BASE_URL")

    if configured_base_url:
        base_url = configured_base_url
        if "openrouter.ai" in base_url:
            api_keys = (generic_api_key or openrouter_api_key or "",)
            default_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
        else:
            api_keys = gemini_api_keys or tuple(
                key for key in (generic_api_key, openrouter_api_key) if key
            )
            default_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    elif gemini_api_keys or generic_api_key:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_keys = gemini_api_keys or (generic_api_key or "",)
        default_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    elif openrouter_api_key:
        base_url = "https://openrouter.ai/api/v1"
        api_keys = (openrouter_api_key,)
        default_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
    else:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_keys = ()
        default_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    api_keys = tuple(dict.fromkeys(key for key in api_keys if key))
    if not api_keys:
        raise ValueError(
            "Set GEMINI_API_KEY (and optional GEMINI_API_KEY1, GEMINI_API_KEY2, ...) "
            "or LLM_API_KEY in the workspace .env file."
        )

    return Settings(
        api_key=api_keys[0],
        api_keys=api_keys,
        base_url=base_url,
        model_name=os.getenv("LLM_MODEL", default_model),
        runs_dir=Path(
            os.getenv(
                "RESEARCH_RUNS_DIR", str(PROJECT_ROOT / "storage" / "research_runs")
            )
        ),
        max_agent_turns=max(1, int(os.getenv("AGENT_MAX_TURNS", "30"))),
        max_research_rounds=max(1, int(os.getenv("RESEARCH_MAX_ROUNDS", "2"))),
    )


def _get_gemini_api_keys() -> tuple[str, ...]:
    indexed_keys = [
        (int(name.removeprefix("GEMINI_API_KEY")), value)
        for name, value in os.environ.items()
        if name.startswith("GEMINI_API_KEY")
        and name.removeprefix("GEMINI_API_KEY").isdigit()
        and value.strip()
    ]
    indexed_keys.sort(key=lambda item: item[0])

    base_key = os.getenv("GEMINI_API_KEY")
    keys = ([base_key] if base_key else []) + [value for _, value in indexed_keys]
    return tuple(dict.fromkeys(keys))
