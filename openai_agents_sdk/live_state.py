import json
from pathlib import Path
from threading import Lock
from typing import Any


class LiveStateStore:
    """Write atomically replaceable JSON snapshots for an active run."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._lock = Lock()
        self._controversial_by_id: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._controversial_by_id.clear()
            self._write("recent_info", [])
            self._write("verified_info", [])
            self._write("controversial_facts", [])

    def write_recent_info(self, items: list[dict[str, Any]]) -> None:
        self._write_threadsafe("recent_info", items)

    def write_verified_info(self, items: list[dict[str, Any]]) -> None:
        self._write_threadsafe("verified_info", items)

    def update_controversial_facts(self, items: list[dict[str, Any]]) -> None:
        with self._lock:
            for item in items:
                self._controversial_by_id.setdefault(item["fact_id"], {}).update(item)
            self._write("controversial_facts", list(self._controversial_by_id.values()))

    def add_controversial_facts(self, items: list[dict[str, Any]]) -> None:
        with self._lock:
            for item in items:
                self._controversial_by_id.setdefault(item["fact_id"], item)
            self._write("controversial_facts", list(self._controversial_by_id.values()))

    def _write_threadsafe(self, name: str, items: list[dict[str, Any]]) -> None:
        with self._lock:
            self._write(name, items)

    def _write(self, name: str, items: list[dict[str, Any]]) -> None:
        path = self.directory / f"{name}.json"
        temporary_path = path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        temporary_path.replace(path)
