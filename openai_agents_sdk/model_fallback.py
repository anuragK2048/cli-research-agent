import asyncio
from collections.abc import AsyncIterator
from threading import Lock
from typing import Any

from agents.models.interface import Model


class RotatingFallbackModel(Model):
    """Try API-key-backed models in round-robin order with quota fallback."""

    def __init__(self, models: list[Model]) -> None:
        if not models:
            raise ValueError("At least one model instance is required.")
        self._models = models
        self._next_index = 0
        self._index_lock = Lock()

    def _starting_index(self) -> int:
        with self._index_lock:
            index = self._next_index
            self._next_index = (self._next_index + 1) % len(self._models)
            return index

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        start_index = self._starting_index()
        last_error: Exception | None = None

        for offset in range(len(self._models)):
            model = self._models[(start_index + offset) % len(self._models)]
            try:
                return await model.get_response(*args, **kwargs)
            except Exception as error:
                if not _is_retryable_provider_error(error):
                    raise
                last_error = error

        if last_error is not None:
            raise last_error
        raise RuntimeError("No model was available for the request.")

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        start_index = self._starting_index()
        last_error: Exception | None = None

        for offset in range(len(self._models)):
            model = self._models[(start_index + offset) % len(self._models)]
            emitted_event = False
            try:
                async for event in model.stream_response(*args, **kwargs):
                    emitted_event = True
                    yield event
                return
            except Exception as error:
                if emitted_event or not _is_retryable_provider_error(error):
                    raise
                last_error = error

        if last_error is not None:
            raise last_error
        raise RuntimeError("No model was available for the streaming request.")


def _is_retryable_provider_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code in {429, 500, 502, 503, 504}:
        return True

    if status_code == 403:
        details = f"{error} {getattr(error, 'body', '')}".casefold()
        return any(
            marker in details
            for marker in ("quota", "rate limit", "resource_exhausted")
        )

    return isinstance(error, (asyncio.TimeoutError, TimeoutError, ConnectionError))
