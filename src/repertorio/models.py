"""Bounded, strict domain records; free text is always data, never instructions."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

MAX_INPUT_BYTES = 1_048_576
MAX_DEPTH = 12
MAX_RECORDS = 1000
MAX_REVISION = 2_147_483_647
Identifier = Annotated[
    str, StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=300)]
Element = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Timestamp = Annotated[str, StringConstraints(min_length=20, max_length=40)]


def bounded_json(value: Any) -> str:
    """Check depth/types before serialization, including cyclic Python values."""
    stack = [(value, 0)]
    nodes = 0
    while stack:
        obj, depth = stack.pop()
        nodes += 1
        if depth > MAX_DEPTH or nodes > 30_000:
            raise ValueError("Input exceeds nesting or element limit.")
        if isinstance(obj, dict):
            if len(obj) + len(stack) > 30_000:
                raise ValueError("Input exceeds element limit.")
            if any(not isinstance(key, str) for key in obj):
                raise ValueError("JSON object keys must be strings.")
            stack.extend((child, depth + 1) for child in obj.values())
        elif isinstance(obj, list):
            if len(obj) + len(stack) > 30_000:
                raise ValueError("Input exceeds element limit.")
            stack.extend((child, depth + 1) for child in obj)
        elif (
            obj is None or isinstance(obj, (str, bool, int)) or isinstance(obj, float) and math.isfinite(obj)
        ):
            pass
        else:
            raise ValueError("Input must contain finite JSON values only.")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 1 MiB limit.")
    return encoded


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True, str_strip_whitespace=False)


class StoredRecord(StrictRecord):
    id: Identifier
    revision: int = Field(default=1, ge=1, le=MAX_REVISION)
    created_at: Timestamp | None = None
    updated_at: Timestamp | None = None

    @field_validator("created_at", "updated_at")
    @classmethod
    def timezone_required(cls, value: str | None) -> str | None:
        if value is not None:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is None:
                raise ValueError("Timestamp must include a timezone.")
        return value


class RepertoireItem(StoredRecord):
    title: ShortText
    kind: Literal["experience", "book", "film", "series", "anime", "game"] = "experience"
    status: Literal["planned", "started", "completed", "abandoned", "unknown"] = "unknown"
    affinity: int = Field(default=0, ge=0, le=5)
    familiarity: int = Field(default=0, ge=0, le=3)
    progress: float | None = Field(default=None, ge=0, le=100)
    spoiler_limit: float | None = Field(default=None, ge=0, le=100)
    elements: list[Element] = Field(default_factory=list, max_length=100)
    excluded: bool = False
    source: Annotated[str, StringConstraints(min_length=1, max_length=120)] = "self_report"
    edition: Annotated[str, StringConstraints(min_length=1, max_length=200)] | None = None
    external_ids: dict[Element, Annotated[str, StringConstraints(min_length=1, max_length=256)]] = Field(
        default_factory=dict, max_length=32
    )
    tags: list[Element] = Field(default_factory=list, max_length=50)
    language: Annotated[str, StringConstraints(min_length=2, max_length=35)] = "en"

    @field_validator("elements", "tags")
    @classmethod
    def unique_values(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("List must not contain duplicates.")
        return value


class Evidence(StoredRecord):
    """Origin is a caller-declared category; none of these values attests correctness."""

    concept: ShortText
    activity_id: Identifier
    activity_version: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    help_received: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    result: ShortText
    origin: Literal["self_report", "imported", "tutor_assessment", "provisional"]
    assessor: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    summary: Annotated[str, StringConstraints(max_length=1200)] | None = None
    session_id: Identifier | None = None
    occurred_at: Timestamp | None = None

    @field_validator("occurred_at")
    @classmethod
    def occurrence_timezone(cls, value: str | None) -> str | None:
        return StoredRecord.timezone_required(value)


class Session(StoredRecord):
    objective: Annotated[str, StringConstraints(max_length=1000)] = ""
    concept: Annotated[str, StringConstraints(max_length=300)] = ""
    catalog_version: Annotated[str, StringConstraints(min_length=1, max_length=80)] = "unknown"
    policy_version: Annotated[str, StringConstraints(min_length=1, max_length=80)] | None = None
    context_reference_ids: list[Identifier] = Field(default_factory=list, max_length=50)
    repertoire_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    evidence_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    client: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None
    model: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None
    usage: Literal["delivered", "reported"] = "delivered"
    usage_origin: Literal["client_reported_delivery", "self_report", "tutor_report"] = (
        "client_reported_delivery"
    )

    @model_validator(mode="after")
    def consistent_usage(self) -> Session:
        if (self.usage == "delivered") != (self.usage_origin == "client_reported_delivery"):
            raise ValueError(
                "Delivery is a client report; reported use requires self_report or tutor_report."
            )
        for values in (self.context_reference_ids, self.repertoire_ids, self.evidence_ids):
            if len(values) != len(set(values)):
                raise ValueError("Reference lists must not contain duplicates.")
        return self


class Profile(StrictRecord):
    schema_version: Literal[1] = 1
    repertoire: list[RepertoireItem] = Field(default_factory=list, max_length=MAX_RECORDS)
    evidence: list[Evidence] = Field(default_factory=list, max_length=MAX_RECORDS)
    sessions: list[Session] = Field(default_factory=list, max_length=MAX_RECORDS)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer.")
        return value

    @model_validator(mode="after")
    def unique_ids(self) -> Profile:
        for values in (self.repertoire, self.evidence, self.sessions):
            ids = [record.id for record in values]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate record IDs are not allowed in one import.")
        return self
