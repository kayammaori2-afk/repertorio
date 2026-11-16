"""Read-only first-use guidance. Never invent familiarity or write a learner profile."""

from __future__ import annotations

import unicodedata
from typing import Any

from .selection import candidate_pool, catalog

TOPICS = {
    "opportunity_cost": ("Custo de oportunidade", "opportunity cost", "custo de oportunidade"),
    "marginal_analysis": ("Análise marginal", "marginal analysis", "analise marginal"),
    "conditional_probability": (
        "Probabilidade condicional",
        "conditional probability",
        "probabilidade condicional",
    ),
    "independence": (
        "Independência estatística",
        "statistical independence",
        "independencia estatistica",
        "independencia",
    ),
}


def normalize(text: str) -> str:
    return " ".join(
        "".join(
            c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
        ).split()
    )


def resolve_topic(topic: str) -> str | None:
    query = normalize(topic)
    for identifier, labels in TOPICS.items():
        if query in {normalize(value) for value in (identifier, *labels)}:
            return identifier
    return None


def learning_options(profile: dict[str, Any], topic: str = "") -> dict[str, Any]:
    """Exact bilingual aliases only; broad or ambiguous prose is never guessed."""
    concept = resolve_topic(topic) if topic else None
    supported = [{"id": key, "label": value[0], "english": value[1]} for key, value in TOPICS.items()]
    result: dict[str, Any] = {
        "supported_topics": supported,
        "resolved_concept": concept,
        "state": "choose_topic" if not topic else "unsupported_topic" if concept is None else "needs_context",
        "saved_item_count": len(profile.get("repertoire", [])),
        "writes_performed": False,
        "options": [],
        "privacy": "Only save facts the learner chooses to share. The assistant/provider receives tool results. No full transcript is required.",
        "next_action": "Offer these four topics in ordinary language. The learner may skip personalization and study directly.",
    }
    if topic and concept is None:
        result["next_action"] = (
            "Explain this topic is outside the reviewed catalog and teach directly. Do not force it into a supported topic."
        )
    if concept is None:
        return result
    eligible, rejected = candidate_pool(profile, concept)
    evaluated_ids = {entry["id"] for entry in eligible + rejected}
    by_id = {entry["id"]: entry["reasons"] for entry in rejected}
    for reference in catalog()["references"]:
        if reference["concept"] != concept or reference["id"] not in evaluated_ids:
            continue
        reasons = by_id.get(reference["id"], [])
        # An explicit exclusion must not become a suggestion to undo that choice.
        if "excluded" in reasons:
            continue
        result["options"].append(
            {
                "reference_id": reference["id"],
                "item_id": reference["item_id"],
                "experience": reference["title"],
                "ready": not reasons,
                "missing_requirements": reasons,
                "requirements": {
                    "status": ["started", "completed", "abandoned"],
                    "elements": reference["required_elements"],
                    "familiarity": reference["required_familiarity"],
                    "edition": reference.get("edition"),
                    "progress": reference.get("required_progress", 0),
                    "spoiler_limit": reference.get("spoiler_position", 0),
                },
            }
        )
    result["state"] = "ready" if eligible else "needs_context"
    result["next_action"] = (
        "Call prepare_context with resolved_concept; do not ask for information already confirmed."
        if eligible
        else "Offer one relevant experience or direct teaching. Requirements are catalog metadata, NOT learner facts. Ask at most one focused question; save only explicitly confirmed facts with save_item, preserving existing fields and expected_revision. If the learner explicitly says they have done this everyday experience, record status completed; use started for explicitly ongoing experiences. Interest alone never establishes status or familiarity. Unknown/planned status blocks selection even with familiarity. Use compact provenance such as self_report. Never copy requirements as a learner's answer. After saving, check learning_options again; explain any remaining eligibility requirement rather than claiming personalization worked. If declined, teach directly."
    )
    return result
