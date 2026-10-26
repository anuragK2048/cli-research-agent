from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ResearchContext:
    """Mutable state scoped to one workflow run and passed only to its tools."""

    recent_info: list[dict[str, Any]] = field(default_factory=list)
    searched_urls: set[str] = field(default_factory=set)
    recent_info_observer: Callable[[list[dict[str, Any]]], None] | None = None

    def add_recent_info(self, items: list[dict[str, Any]]) -> None:
        self.recent_info.extend(items)
        if self.recent_info_observer:
            self.recent_info_observer(self.recent_info)

    def clear_recent_info(self) -> None:
        self.recent_info.clear()
        if self.recent_info_observer:
            self.recent_info_observer(self.recent_info)

    def start_tool_session(self) -> None:
        self.searched_urls.clear()
