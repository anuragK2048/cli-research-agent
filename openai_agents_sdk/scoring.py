from collections.abc import Iterable
from typing import Any

SOURCE_WEIGHTS = {"primary": 1.0, "secondary": 0.5, "unknown": 0.1}
STANCE_WEIGHTS = {"direct": 1.0, "indirect": 0.6, "partial": 0.4}


def compute_confidence(
    evidence_for: Iterable[dict[str, Any]],
    evidence_against: Iterable[dict[str, Any]],
) -> float:
    supporting_score = sum(_evidence_score(item) for item in evidence_for)
    contradicting_score = sum(_evidence_score(item) for item in evidence_against)
    total = supporting_score + contradicting_score
    if total == 0:
        return 0.0
    return round(abs(supporting_score - contradicting_score) / total, 2)


def _evidence_score(item: dict[str, Any]) -> float:
    source_weight = SOURCE_WEIGHTS.get(item.get("source_type", "unknown"), 0.1)
    stance_weight = STANCE_WEIGHTS.get(item.get("stance_strength", "partial"), 0.4)
    return source_weight * stance_weight
