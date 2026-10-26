import argparse

from .settings import load_settings
from .workflow import run_research


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an evidence-grounded research agent."
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="The research question. If omitted, you will be prompted for it.",
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
        request = args.request or input("Research question: ").strip()
        result = run_research(
            request,
            settings,
            clarification_provider=lambda question: input(f"{question}\n> ").strip(),
            progress=lambda message: print(message, flush=True),
        )
    except (KeyboardInterrupt, EOFError):
        print("Research cancelled.")
        return 130
    except Exception as error:
        print(f"Research failed: {error}")
        return 1

    print("\n" + result["final_report"])
    print(f"\nRun artifact: {result['artifact_path']}")
    return 0
