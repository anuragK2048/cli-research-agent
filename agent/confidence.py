SOURCE_WEIGHTS = {
    "primary": 1.0,
    "official": 0.9,
    "reputable_news": 0.7,
    "secondary": 0.5,
    "blog_forum": 0.2,
    "unknown": 0.1,
}

STANCE_WEIGHTS = {
    "direct": 1.0,
    "indirect": 0.6,
    "partial": 0.4,
}

# def recency_weight(published_date, half_life_days=365):
#     age_days = (today - published_date).days
#     return 0.5 ** (age_days / half_life_days)   # exponential decay

def evidence_score(evidence_item):
    return (
        SOURCE_WEIGHTS[evidence_item["source_type"]]
        * STANCE_WEIGHTS[evidence_item["stance_strength"]]
        # * recency_weight(evidence_item["published_date"])
    )

def compute_confidence(evidence_for, evidence_against):
    for_score = sum(evidence_score(e) for e in evidence_for)
    against_score = sum(evidence_score(e) for e in evidence_against)

    total = for_score + against_score
    if total == 0:
        return {"verdict": "unresolved", "confidence": 0.0}

    net = (for_score - against_score) / total   # range -1 to 1
    confidence = abs(net)
    verdict = "supported" if net > 0 else "contradicted" if net < 0 else "disputed"

    return {"verdict": verdict, "confidence": round(confidence, 2), "for_score": for_score, "against_score": against_score}