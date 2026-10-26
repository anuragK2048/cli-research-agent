"""Compatibility entry point; prefer `python -m openai_agents_sdk`."""

from openai_agents_sdk.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
