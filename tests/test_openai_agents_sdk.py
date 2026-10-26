import json
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from openai_agents_sdk.context import ResearchContext
from openai_agents_sdk.live_state import LiveStateStore
from openai_agents_sdk.models import (
    AdjudicationOutput,
    CoverageOutput,
    PlanOutput,
    SubTopic,
)
from openai_agents_sdk.model_fallback import RotatingFallbackModel
from openai_agents_sdk.scoring import compute_confidence
from openai_agents_sdk.settings import Settings, load_settings
from openai_agents_sdk.tools import _require_searched_url
from openai_agents_sdk.workflow import (
    _create_run_config,
    _create_provider_model,
    _save_artifact,
    _stable_fact_id,
    _verified_disputed_facts,
)


class _FakeProviderError(Exception):
    status_code = 429


class _FakeModel:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    async def get_response(self, *args: object, **kwargs: object) -> object:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    async def stream_response(self, *args: object, **kwargs: object):
        if self.error:
            raise self.error
        yield self.result


class ResearchAgentTests(unittest.TestCase):
    def test_live_state_clear_and_incremental_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LiveStateStore(Path(directory))
            store.clear()
            store.write_recent_info([{"chunk_id": "chunk-1"}])
            store.add_controversial_facts([{"fact_id": "fact-1", "evidence_for": []}])
            store.update_controversial_facts(
                [{"fact_id": "fact-1", "evidence_for": [{"chunk_id": "chunk-2"}]}]
            )
            store.write_verified_info([{"id": "fact-1"}])

            controversial = json.loads(
                (Path(directory) / "controversial_facts.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(controversial[0]["evidence_for"][0]["chunk_id"], "chunk-2")
            self.assertEqual(
                json.loads(
                    (Path(directory) / "recent_info.json").read_text(encoding="utf-8")
                ),
                [{"chunk_id": "chunk-1"}],
            )

            store.clear()
            observed_chunks: list[dict[str, str]] = []
            context = ResearchContext(
                recent_info_observer=lambda items: observed_chunks.extend(items)
            )
            context.add_recent_info([{"chunk_id": "observed-chunk"}])
            self.assertEqual(observed_chunks, [{"chunk_id": "observed-chunk"}])

            for filename in ("recent_info", "verified_info", "controversial_facts"):
                with self.subTest(filename=filename):
                    self.assertEqual(
                        json.loads(
                            (Path(directory) / f"{filename}.json").read_text(
                                encoding="utf-8"
                            )
                        ),
                        [],
                    )

    def test_shared_run_config_limits_tool_concurrency(self) -> None:
        run_config = _create_run_config("test-model")

        self.assertIsNone(run_config.model_settings)
        self.assertEqual(
            run_config.tool_execution.max_function_tool_concurrency,
            5,
        )

    def test_gemini_openai_compatible_settings(self) -> None:
        with patch("openai_agents_sdk.settings.load_dotenv"), patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-gemini-key", "GEMINI_MODEL": "gemini-test-model"},
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.api_key, "test-gemini-key")
        self.assertEqual(
            settings.base_url,
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.assertEqual(settings.model_name, "gemini-test-model")
        self.assertEqual(settings.api_keys, ("test-gemini-key",))

    def test_numbered_gemini_keys_are_sorted_and_deduplicated(self) -> None:
        with patch("openai_agents_sdk.settings.load_dotenv"), patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY3": "key-three",
                "GEMINI_API_KEY1": "key-one",
                "GEMINI_API_KEY2": "key-two",
                "GEMINI_API_KEY": "key-one",
            },
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.api_keys, ("key-one", "key-two", "key-three"))
        self.assertEqual(settings.api_key, "key-one")

    def test_openrouter_key_selects_openrouter_endpoint(self) -> None:
        with patch("openai_agents_sdk.settings.load_dotenv"), patch.dict(
            "os.environ",
            {"OPENROUTER_API_KEY": "test-openrouter-key"},
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.api_key, "test-openrouter-key")
        self.assertEqual(settings.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(settings.model_name, "openai/gpt-4.1-mini")

    def test_provider_factory_creates_one_model_per_key(self) -> None:
        with patch("openai_agents_sdk.workflow.AsyncOpenAI") as client_factory, patch(
            "openai_agents_sdk.workflow.OpenAIChatCompletionsModel"
        ) as model_factory:
            settings = Settings(
                api_key="key-one",
                api_keys=("key-one", "key-two"),
                base_url="https://example.test/v1",
                model_name="test-model",
                runs_dir=Path("runs"),
            )
            model = _create_provider_model(settings)

        self.assertIsInstance(model, RotatingFallbackModel)
        self.assertEqual(client_factory.call_count, 2)
        self.assertEqual(model_factory.call_count, 2)
        self.assertEqual(
            [call.kwargs["api_key"] for call in client_factory.call_args_list],
            ["key-one", "key-two"],
        )

    def test_rotating_model_falls_back_after_rate_limit(self) -> None:
        first = _FakeModel(error=_FakeProviderError("quota exceeded"))
        second = _FakeModel(result="second-key-result")
        model = RotatingFallbackModel([first, second])

        result = asyncio.run(model.get_response())

        self.assertEqual(result, "second-key-result")
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)

    def test_rotating_model_does_not_fallback_on_other_errors(self) -> None:
        first = _FakeModel(error=ValueError("invalid request"))
        second = _FakeModel(result="should-not-run")
        model = RotatingFallbackModel([first, second])

        with self.assertRaisesRegex(ValueError, "invalid request"):
            asyncio.run(model.get_response())
        self.assertEqual(second.calls, 0)

    def test_rotating_model_advances_start_key_between_requests(self) -> None:
        models = [_FakeModel(result=index) for index in range(3)]
        model = RotatingFallbackModel(models)

        first_result = asyncio.run(model.get_response())
        second_result = asyncio.run(model.get_response())

        self.assertEqual((first_result, second_result), (0, 1))
        self.assertEqual([provider.calls for provider in models], [1, 1, 0])

    def test_plan_requires_at_least_three_topics(self) -> None:
        with self.assertRaises(ValidationError):
            PlanOutput(
                sub_topics=[SubTopic(name="Only topic", check_list=["One question"])]
            )

    def test_coverage_requires_gap_report_to_match_status(self) -> None:
        with self.assertRaises(ValidationError):
            CoverageOutput(requirement_fulfilled=True, gap_report=["Missing data"])
        with self.assertRaises(ValidationError):
            CoverageOutput(requirement_fulfilled=False, gap_report=None)

    def test_confidence_weights_source_and_stance(self) -> None:
        evidence_for = [{"source_type": "primary", "stance_strength": "direct"}]
        evidence_against = [{"source_type": "secondary", "stance_strength": "indirect"}]

        self.assertEqual(compute_confidence(evidence_for, evidence_against), 0.54)
        self.assertEqual(compute_confidence([], []), 0.0)

    def test_fetch_requires_url_from_current_searches(self) -> None:
        context = ResearchContext()
        url = "https://example.com/report"

        with self.assertRaises(ValueError):
            _require_searched_url(context, url)
        context.searched_urls.add(url)
        _require_searched_url(context, url)
        context.start_tool_session()
        with self.assertRaises(ValueError):
            _require_searched_url(context, url)

    def test_fact_ids_are_stable_and_missing_adjudications_are_kept(self) -> None:
        first_id = _stable_fact_id(1, "Provider comparison", "GPU supply differs")
        normalized_id = _stable_fact_id(
            1, "PROVIDER COMPARISON", " GPU supply  differs "
        )
        other_topic_id = _stable_fact_id(2, "Provider comparison", "GPU supply differs")
        self.assertEqual(first_id, normalized_id)
        self.assertNotEqual(first_id, other_topic_id)

        verified = _verified_disputed_facts(
            [
                {
                    "fact_id": first_id,
                    "claim": "GPU supply differs",
                    "source_chunk_ids": ["c1"],
                }
            ],
            AdjudicationOutput(result=[]),
        )
        self.assertEqual(verified[0]["status"], "unresolved")

    def test_run_artifact_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = _save_artifact(
                Path(directory), "test-run", {"final_report": "A report"}
            )

            self.assertEqual(
                json.loads(artifact_path.read_text(encoding="utf-8")),
                {"final_report": "A report"},
            )


if __name__ == "__main__":
    unittest.main()
