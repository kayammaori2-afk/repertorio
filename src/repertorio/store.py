"""Scoped SQLite persistence, atomic imports, CAS writes and bounded deletion.

Storage schema v1: records(profile, kind, id, revision, body), composite PK.
Storage schema v2 adds requests and deletion_tokens. Schema v3 normalizes old
records and removes identifying replay/deletion metadata. Schema v4 persists
catalog reference dependencies on repertoire records. Portable JSON version
is independent and remains 1. All SQL containing values is parameterized.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import (
    MAX_INPUT_BYTES,
    MAX_RECORDS,
    MAX_REVISION,
    Evidence,
    Profile,
    RepertoireItem,
    Session,
    bounded_json,
)
from .selection import catalog

DB_VERSION = 4
DELETE_TTL_SECONDS = 300
KINDS = ("repertoire", "evidence", "sessions")
MODELS = {"repertoire": RepertoireItem, "evidence": Evidence, "sessions": Session}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_METADATA = {"revision", "created_at", "updated_at"}


class StoreError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_input", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ConflictError(StoreError):
    def __init__(self, message: str, current_revision: int | None = None) -> None:
        super().__init__(message, code="conflict")
        self.current_revision = current_revision


def _stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identifier(value: Any, label: str = "ID") -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise StoreError(f"{label} must be 1..128 letters, digits, dots, colons, underscores or hyphens.")
    return value


def _migration_error() -> StoreError:
    return StoreError(
        "Migration cannot validate a legacy record; all migration changes were rolled back. "
        "Keep a database backup and inspect the legacy records and their repertoire links locally before retrying.",
        code="migration_invalid_record",
    )


def _validated(model: Any, value: Any) -> Any:
    try:
        bounded_json(value)
        return model.model_validate(value)
    except ValidationError as exc:
        first = exc.errors(include_input=False, include_url=False)[0]
        location = ".".join(str(part) for part in first["loc"]) or "record"
        # Do not copy caller text or Pydantic's context values into errors/logs.
        raise StoreError(f"Invalid {location}: {first['type']}. Check the tool schema.") from None
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise StoreError("Input violates the JSON size, nesting or value limits.") from exc


class Store:
    """A profile-scoped repository. Authorization belongs to the transport.

    The process/verified credential supplies profile; no method accepts a
    profile selector. A new connection per operation supports multiple clients.

    Callers must generate random, nonsemantic request IDs (for example UUID4)
    and reuse one only to retry the same operation. The syntax validator does
    not enforce randomness. Deletion retains deterministic, profile-scoped
    request-key hashes to prevent delayed retries recreating removed records.
    A database reader can confirm a guessed profile/request-ID pair; a caller
    with access to that profile can observe its retired-request response. These
    markers are not encryption or complete identifier erasure. Never encode
    record IDs, titles, personal data or operation meaning in request IDs.
    """

    def __init__(self, path: str | Path, profile: str) -> None:
        self.profile = _identifier(profile, "Configured profile")
        self.path = Path(path)
        if str(path) == ":memory:":
            raise StoreError(
                "Choose a persistent database path; per-operation connections do not support :memory:."
            )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._migrate()
            if os.name != "nt":
                self.path.chmod(0o600)
        except OSError as exc:
            raise StoreError(
                "Cannot open the configured database. Check its directory and permissions.",
                code="storage_unavailable",
                retryable=True,
            ) from exc

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA secure_delete=ON")
        return connection

    @contextmanager
    def _transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = None
        try:
            connection = self._connection()
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise StoreError(
                "Database operation failed; no change was committed. Retry or run doctor.",
                code="storage_unavailable",
                retryable=True,
            ) from exc
        except BaseException:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def _migrate(self) -> None:
        # DDL, record normalization and schema markers share one transaction.
        with self._transaction(write=True) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > DB_VERSION:
                raise StoreError("Database schema is newer than this application; upgrade before opening it.")
            if version < 1:
                connection.execute("""CREATE TABLE records (
                    profile TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK(revision >= 1), body TEXT NOT NULL,
                    PRIMARY KEY(profile, kind, id), CHECK(kind IN ('repertoire','evidence','sessions'))
                )""")
                connection.execute("PRAGMA user_version=1")
            if version < 2:
                connection.execute("""CREATE TABLE requests (
                    profile TEXT NOT NULL, request_id TEXT NOT NULL, operation TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, result TEXT, retired INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(profile, request_id)
                )""")
                connection.execute("""CREATE TABLE deletion_tokens (
                    token_hash TEXT PRIMARY KEY, profile TEXT NOT NULL, kind TEXT NOT NULL,
                    ids TEXT NOT NULL, snapshot TEXT NOT NULL, expires_at REAL NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0
                )""")
                connection.execute("CREATE INDEX deletion_profile ON deletion_tokens(profile)")
                connection.execute("PRAGMA user_version=2")
            if version < 3:
                stamp = _stamp()
                for row in connection.execute("SELECT * FROM records").fetchall():
                    try:
                        value = json.loads(row["body"])
                    except (ValueError, TypeError) as exc:
                        raise _migration_error() from exc
                    if not isinstance(value, dict) or row["kind"] not in MODELS:
                        raise _migration_error()
                    value.setdefault("id", row["id"])
                    value.setdefault("revision", row["revision"])
                    if value["id"] != row["id"] or value["revision"] != row["revision"]:
                        raise _migration_error()
                    if row["kind"] == "sessions" and value.get("usage_origin") == "server_delivery":
                        value["usage_origin"] = "client_reported_delivery"
                    try:
                        normalized = _validated(MODELS[row["kind"]], value).model_dump(mode="json")
                    except StoreError as exc:
                        raise _migration_error() from exc
                    normalized["created_at"] = normalized["created_at"] or normalized["updated_at"] or stamp
                    normalized["updated_at"] = normalized["updated_at"] or normalized["created_at"]
                    connection.execute(
                        "UPDATE records SET body=? WHERE profile=? AND kind=? AND id=?",
                        (_json(normalized), row["profile"], row["kind"], row["id"]),
                    )
                # Retire pre-release receipts: their shapes/provenance may be
                # obsolete. Preserve deterministic request-key hashes for
                # retries; guessed profile/request-ID pairs remain confirmable.
                connection.execute("""CREATE TABLE requests_v3 (
                    profile TEXT NOT NULL, request_id TEXT NOT NULL, operation TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, result TEXT, retired INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(profile, request_id)
                )""")
                for row in connection.execute("SELECT profile,request_id FROM requests").fetchall():
                    connection.execute(
                        "INSERT INTO requests_v3 VALUES(?,?,'','',NULL,1)",
                        (row["profile"], _hash(_json([row["profile"], row["request_id"]]))),
                    )
                connection.execute("DROP TABLE requests")
                connection.execute("ALTER TABLE requests_v3 RENAME TO requests")
                # Previous previews no longer describe normalized records.
                connection.execute("UPDATE deletion_tokens SET kind='',ids='[]',snapshot='',consumed=1")
                connection.execute("PRAGMA user_version=3")
            if version < 4:
                changed_profiles = set()
                for row in connection.execute("SELECT * FROM records WHERE kind='sessions'").fetchall():
                    try:
                        previous = json.loads(row["body"])
                        normalized = self._bind_session(previous)
                    except (ValueError, TypeError) as exc:
                        raise _migration_error() from exc
                    if normalized != previous:
                        connection.execute(
                            "UPDATE records SET body=? WHERE profile=? AND kind='sessions' AND id=?",
                            (_json(normalized), row["profile"], row["id"]),
                        )
                        changed_profiles.add(row["profile"])
                for profile in changed_profiles:
                    records: dict[str, list[dict[str, Any]]] = {kind: [] for kind in KINDS}
                    for row in connection.execute(
                        "SELECT kind,body FROM records WHERE profile=?", (profile,)
                    ):
                        records[row["kind"]].append(json.loads(row["body"]))
                    try:
                        self._check_links(records)
                        self._check_profile_size(records)
                    except StoreError as exc:
                        raise _migration_error() from exc
                    connection.execute(
                        "UPDATE requests SET operation='',payload_hash='',result=NULL,retired=1 WHERE profile=?",
                        (profile,),
                    )
                    connection.execute(
                        "UPDATE deletion_tokens SET kind='',ids='[]',snapshot='',consumed=1 WHERE profile=?",
                        (profile,),
                    )
                connection.execute("PRAGMA user_version=4")
            connection.execute(
                "DELETE FROM deletion_tokens WHERE profile=? AND expires_at<=?", (self.profile, time.time())
            )
        # WAL mode persists for later connections; no records change here.
        journal_connection = None
        try:
            journal_connection = self._connection()
            journal_connection.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error as exc:
            raise StoreError(
                "Cannot initialize database journal mode. Retry or run doctor.",
                code="storage_unavailable",
                retryable=True,
            ) from exc
        finally:
            if journal_connection is not None:
                journal_connection.close()

    def _request(self, request_id: str, operation: str, payload: Any) -> tuple[str, str, str]:
        # Hashing avoids plaintext request IDs, but is not encryption: a reader
        # can recompute a guessed pair. Callers must use random nonsemantic IDs.
        _identifier(request_id, "request_id")
        try:
            return _hash(_json([self.profile, request_id])), operation, _hash(bounded_json(payload))
        except (ValueError, TypeError, RecursionError, OverflowError) as exc:
            raise StoreError("Input violates the JSON size, nesting or value limits.") from exc

    def _replay(self, connection: sqlite3.Connection, request: tuple[str, str, str]) -> Any | None:
        key, operation, digest = request
        row = connection.execute(
            "SELECT * FROM requests WHERE profile=? AND request_id=?", (self.profile, key)
        ).fetchone()
        if row is None:
            return None
        if row["retired"]:
            raise StoreError(
                "This request was retired by deletion or schema migration. Read current state; do not retry.",
                code="deleted_result",
            )
        if row["operation"] != operation or row["payload_hash"] != digest:
            raise ConflictError("request_id was already used for different content. Use a new request_id.")
        return json.loads(row["result"])

    def _remember(self, connection: sqlite3.Connection, request: tuple[str, str, str], result: Any) -> None:
        connection.execute(
            "INSERT INTO requests(profile,request_id,operation,payload_hash,result) VALUES(?,?,?,?,?)",
            (self.profile, *request, _json(result)),
        )

    def _records(self, connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {kind: [] for kind in KINDS}
        rows = connection.execute(
            "SELECT kind,body FROM records WHERE profile=? ORDER BY kind,id", (self.profile,)
        )
        for row in rows:
            result[row["kind"]].append(json.loads(row["body"]))
        return result

    def get_profile(self) -> dict[str, Any]:
        with self._transaction() as connection:
            return {"schema_version": 1, **self._records(connection)}

    def export_profile(self) -> dict[str, Any]:
        # No machine identity, file paths, credentials, replay payloads or tokens.
        return self.get_profile()

    def _find(self, connection: sqlite3.Connection, kind: str, identifier: str) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT body FROM records WHERE profile=? AND kind=? AND id=?", (self.profile, kind, identifier)
        ).fetchone()
        return None if row is None else json.loads(row["body"])

    def _put(self, connection: sqlite3.Connection, kind: str, record: dict[str, Any]) -> None:
        connection.execute(
            """INSERT INTO records(profile,kind,id,revision,body) VALUES(?,?,?,?,?)
            ON CONFLICT(profile,kind,id) DO UPDATE SET revision=excluded.revision,body=excluded.body""",
            (self.profile, kind, record["id"], record["revision"], _json(record)),
        )

    def _check_capacity(self, connection: sqlite3.Connection, kind: str) -> None:
        count = connection.execute(
            "SELECT count(*) FROM records WHERE profile=? AND kind=?", (self.profile, kind)
        ).fetchone()[0]
        if count > MAX_RECORDS:
            raise StoreError(
                f"Profile exceeds {MAX_RECORDS} {kind} records. Export and remove old records first."
            )

    @staticmethod
    def _check_profile_size(records: dict[str, list[dict[str, Any]]]) -> None:
        # A valid active profile must always fit its own portable import format.
        # Per-record caps alone would allow exports too large to restore.
        try:
            bounded_json({"schema_version": 1, **records})
        except (ValueError, TypeError, RecursionError, OverflowError) as exc:
            raise StoreError(
                "Profile would exceed its portable size limit. Export and remove old records first."
            ) from exc

    def _check_links(self, records: dict[str, list[dict[str, Any]]]) -> None:
        ids = {kind: {item["id"] for item in records[kind]} for kind in KINDS}
        for evidence in records["evidence"]:
            if evidence.get("session_id") is not None and evidence["session_id"] not in ids["sessions"]:
                raise StoreError("Evidence session_id does not exist in the authenticated profile.")
        for session in records["sessions"]:
            if any(identifier not in ids["repertoire"] for identifier in session.get("repertoire_ids", [])):
                raise StoreError("Session repertoire reference does not exist in the authenticated profile.")
            if any(identifier not in ids["evidence"] for identifier in session.get("evidence_ids", [])):
                raise StoreError("Session evidence reference does not exist in the authenticated profile.")

    @staticmethod
    def _bind_session(record: dict[str, Any]) -> dict[str, Any]:
        """Persist item dependencies; historical/unknown references need declared links.

        Explicit historical links are caller-declared, not attested. They are
        retained across catalog changes so deletion does not depend on a future
        catalog still containing today's reference IDs.
        """
        references = record.get("context_reference_ids", [])
        if not references:
            return record
        current_catalog = catalog()
        mapping = {ref["id"]: ref["item_id"] for ref in current_catalog["references"]}
        linked = list(record.get("repertoire_ids", []))
        current_version = record.get("catalog_version", "unknown") in ("unknown", current_catalog["version"])
        unknown_references = any(reference not in mapping for reference in references)
        if (not current_version or unknown_references) and not linked:
            raise StoreError(
                "Unknown catalog version or reference requires explicit repertoire_ids for every referenced item. "
                "Supply the historical item links or omit unsupported context references."
            )
        if current_version:
            linked.extend(sorted({mapping[ref] for ref in references if ref in mapping} - set(linked)))
        result = {**record, "repertoire_ids": linked}
        if record.get("catalog_version", "unknown") == "unknown" and not unknown_references:
            result["catalog_version"] = current_catalog["version"]
        return _validated(Session, result).model_dump(mode="json")

    def save_item(
        self, item: dict[str, Any], request_id: str, expected_revision: int | None = None
    ) -> dict[str, Any]:
        """Save with CAS; request_id must be random, nonsemantic and stable for retries."""
        request = self._request(
            request_id, "save_item", {"item": item, "expected_revision": expected_revision}
        )
        if not isinstance(item, dict):
            raise StoreError("item must be a JSON object.")
        identifier = _identifier(item.get("id"))
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 1):
            raise StoreError("expected_revision must be a positive integer.")
        with self._transaction(write=True) as connection:
            replay = self._replay(connection, request)
            if replay is not None:
                return replay
            current = self._find(connection, "repertoire", identifier)
            if current is not None:
                if expected_revision != current["revision"]:
                    raise ConflictError(
                        "Item changed or expected_revision was omitted. Read current profile and reapply edits.",
                        current["revision"],
                    )
                for field in _METADATA:
                    if field in item and item[field] != current[field]:
                        raise ConflictError(
                            "Server metadata cannot be changed; read the latest item.", current["revision"]
                        )
                proposed = _validated(RepertoireItem, {**current, **item}).model_dump(mode="json")
                if proposed == current:
                    self._remember(connection, request, current)
                    return current
                if current["revision"] >= MAX_REVISION:
                    raise StoreError(
                        "Item revision limit reached. Export this profile and create a new item ID.",
                        code="revision_limit",
                    )
                proposed["revision"] = current["revision"] + 1
                proposed["updated_at"] = _stamp()
            else:
                if expected_revision is not None:
                    raise ConflictError(
                        "Item does not exist. Create without expected_revision after checking current state."
                    )
                if any(field in item for field in _METADATA):
                    raise StoreError(
                        "Creation timestamps and revisions are server-generated; use import for restoration."
                    )
                proposed = _validated(RepertoireItem, item).model_dump(mode="json")
                proposed["created_at"] = proposed["updated_at"] = _stamp()
            self._put(connection, "repertoire", proposed)
            self._check_capacity(connection, "repertoire")
            self._check_profile_size(self._records(connection))
            self._remember(connection, request, proposed)
            return proposed

    def _append(self, kind: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        request = self._request(request_id, "record_" + kind, payload)
        if not isinstance(payload, dict):
            raise StoreError("Record must be a JSON object.")
        with self._transaction(write=True) as connection:
            replay = self._replay(connection, request)
            if replay is not None:
                return replay
            if any(field in payload for field in _METADATA):
                raise StoreError(
                    "Creation timestamps and revisions are server-generated; use import for restoration."
                )
            value = dict(payload)
            if "id" not in value:
                value["id"] = str(uuid.uuid4())
            record = _validated(MODELS[kind], value).model_dump(mode="json")
            if kind == "sessions":
                record = self._bind_session(record)
            current = self._find(connection, kind, record["id"])
            if current is not None:
                if {k: v for k, v in current.items() if k not in _METADATA} != {
                    k: v for k, v in record.items() if k not in _METADATA
                }:
                    raise ConflictError(
                        "Record ID exists with different content. Use a new ID; immutable evidence is not overwritten.",
                        current["revision"],
                    )
                self._remember(connection, request, current)
                return current
            record["created_at"] = record["updated_at"] = _stamp()
            self._put(connection, kind, record)
            self._check_capacity(connection, kind)
            records = self._records(connection)
            self._check_links(records)
            self._check_profile_size(records)
            self._remember(connection, request, record)
            return record

    def record_evidence(self, evidence: dict[str, Any], request_id: str) -> dict[str, Any]:
        """Append a declared origin, not an attestation; use a random nonsemantic request_id."""
        return self._append("evidence", evidence, request_id)

    def record_session(self, session: dict[str, Any], request_id: str) -> dict[str, Any]:
        """Append client-reported provenance; use a random nonsemantic request_id."""
        return self._append("sessions", session, request_id)

    def import_profile(
        self, payload: dict[str, Any], request_id: str, dry_run: bool = True
    ) -> dict[str, Any]:
        """Preserve declared provenance atomically; use a random nonsemantic request_id."""
        if type(dry_run) is not bool:
            raise StoreError("dry_run must be a boolean.")
        request = self._request(request_id, "import_profile", payload)
        if not isinstance(payload, dict) or "schema_version" not in payload:
            raise StoreError("Import must include schema_version: 1.")
        profile = _validated(Profile, payload)
        with self._transaction(write=not dry_run) as connection:
            if not dry_run:
                replay = self._replay(connection, request)
                if replay is not None:
                    return replay
            current = self._records(connection)
            merged = {kind: {record["id"]: record for record in current[kind]} for kind in KINDS}
            counts = {kind: {"added": 0, "unchanged": 0} for kind in KINDS}
            conflicts: list[dict[str, Any]] = []
            pending: list[tuple[str, dict[str, Any]]] = []
            stamp = _stamp()
            for kind in KINDS:
                for incoming in getattr(profile, kind):
                    record = incoming.model_dump(mode="json")
                    if kind == "sessions":
                        record = self._bind_session(record)
                    existing = merged[kind].get(record["id"])
                    if existing is not None:
                        compare_keys = set(record) - (_METADATA - incoming.model_fields_set)
                        if any(record[key] != existing.get(key) for key in compare_keys):
                            conflicts.append(
                                {"kind": kind, "id": record["id"], "current_revision": existing["revision"]}
                            )
                        else:
                            counts[kind]["unchanged"] += 1
                        continue
                    record["created_at"] = record["created_at"] or stamp
                    record["updated_at"] = record["updated_at"] or record["created_at"]
                    merged[kind][record["id"]] = record
                    pending.append((kind, record))
                    counts[kind]["added"] += 1
                if len(merged[kind]) > MAX_RECORDS:
                    raise StoreError(f"Import would exceed {MAX_RECORDS} {kind} records.")
            merged_records = {kind: list(values.values()) for kind, values in merged.items()}
            self._check_links(merged_records)
            self._check_profile_size(merged_records)
            result = {"dry_run": dry_run, "counts": counts, "conflicts": conflicts, "committed": False}
            if dry_run:
                return result
            if conflicts:
                raise ConflictError(
                    "Import conflicts with existing IDs; nothing was imported. Use dry_run to inspect conflicts."
                )
            for kind, record in pending:
                self._put(connection, kind, record)
            result["committed"] = True
            self._remember(connection, request, result)
            return result

    def import_csv(self, text: str, request_id: str, dry_run: bool = True) -> dict[str, Any]:
        if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
            raise StoreError("CSV must be text no larger than 1 MiB.")
        # No path/file/URL interpretation. JSON fields preserve lists, IDs and provenance.
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
            if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise StoreError("CSV requires unique column headers.")
            allowed = set(RepertoireItem.model_fields)
            if not {"id", "title"}.issubset(reader.fieldnames) or not set(reader.fieldnames).issubset(
                allowed
            ):
                raise StoreError("CSV requires id,title and only documented repertoire columns.")
            items: list[dict[str, Any]] = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise StoreError("CSV row has a different number of fields than its header.")
                item: dict[str, Any] = {key: value for key, value in row.items() if value != ""}
                for key in ("affinity", "familiarity", "revision"):
                    if key in item:
                        item[key] = int(item[key])
                for key in ("progress", "spoiler_limit"):
                    if key in item:
                        item[key] = float(item[key])
                if "excluded" in item:
                    if item["excluded"].lower() not in ("true", "false"):
                        raise StoreError("CSV excluded must be true or false.")
                    item["excluded"] = item["excluded"].lower() == "true"
                for key in ("elements", "tags", "external_ids"):
                    if key in item:
                        item[key] = json.loads(item[key])
                items.append(item)
                if len(items) > MAX_RECORDS:
                    raise StoreError(f"CSV exceeds {MAX_RECORDS} records.")
        except (csv.Error, ValueError, TypeError, OverflowError, RecursionError) as exc:
            if isinstance(exc, StoreError):
                raise
            raise StoreError(
                "Invalid CSV value or encoding. Check numeric, boolean and JSON columns."
            ) from exc
        return self.import_profile({"schema_version": 1, "repertoire": items}, request_id, dry_run)

    def export_csv(self) -> str:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(RepertoireItem.model_fields), lineterminator="\n")
        writer.writeheader()
        for record in self.get_profile()["repertoire"]:
            row = dict(record)
            for key in ("elements", "tags", "external_ids"):
                row[key] = _json(row[key])
            row["excluded"] = "true" if row["excluded"] else "false"
            writer.writerow(row)
        return stream.getvalue()

    @staticmethod
    def _selection(
        records: dict[str, list[dict[str, Any]]], kind: str, identifiers: list[str]
    ) -> dict[str, dict[str, dict[str, Any]]]:
        all_records = {group: {record["id"]: record for record in records[group]} for group in KINDS}
        catalog_items = {reference["id"]: reference["item_id"] for reference in catalog()["references"]}
        selected: dict[str, dict[str, dict[str, Any]]] = {group: {} for group in KINDS}
        if kind == "all":
            return all_records
        for identifier in identifiers:
            if identifier not in all_records[kind]:
                raise ConflictError(
                    "A selected record is missing. Read the profile and prepare deletion again."
                )
            selected[kind][identifier] = all_records[kind][identifier]
        # Compute dependent closure. No remaining product record may retain a
        # link or cached context for the selected records.
        changed = True
        while changed:
            changed = False
            for session in records["sessions"]:
                identifier = session["id"]
                if identifier not in selected["sessions"] and (
                    set(session.get("repertoire_ids", [])) & set(selected["repertoire"])
                    or {
                        catalog_items[ref]
                        for ref in session.get("context_reference_ids", [])
                        if ref in catalog_items
                    }
                    & set(selected["repertoire"])
                    or set(session.get("evidence_ids", [])) & set(selected["evidence"])
                ):
                    selected["sessions"][identifier] = session
                    changed = True
            for evidence in records["evidence"]:
                identifier = evidence["id"]
                if (
                    identifier not in selected["evidence"]
                    and evidence.get("session_id") in selected["sessions"]
                ):
                    selected["evidence"][identifier] = evidence
                    changed = True
        return selected

    @staticmethod
    def _snapshot(selected: dict[str, dict[str, dict[str, Any]]]) -> str:
        return _hash(_json(selected))

    def prepare_delete(self, kind: str, ids: list[str]) -> dict[str, Any]:
        if kind not in (*KINDS, "all"):
            raise StoreError("Deletion kind must be repertoire, evidence, sessions or all.")
        if not isinstance(ids, list) or len(ids) > MAX_RECORDS:
            raise StoreError("Deletion ids must be a unique list of at most 1000 IDs.")
        for identifier in ids:
            _identifier(identifier)
        if len(ids) != len(set(ids)):
            raise StoreError("Deletion ids must be a unique list of at most 1000 IDs.")
        if (kind == "all" and ids) or (kind != "all" and not ids):
            raise StoreError("Use empty ids only with kind=all; otherwise select at least one ID.")
        with self._transaction(write=True) as connection:
            connection.execute(
                "DELETE FROM deletion_tokens WHERE profile=? AND expires_at<=?", (self.profile, time.time())
            )
            selected = self._selection(self._records(connection), kind, ids)
            token = secrets.token_urlsafe(32)
            expires = time.time() + DELETE_TTL_SECONDS
            connection.execute(
                """INSERT INTO deletion_tokens(token_hash,profile,kind,ids,snapshot,expires_at)
                VALUES(?,?,?,?,?,?)""",
                (
                    _hash(token),
                    self.profile,
                    kind,
                    _json(sorted(ids)),
                    self._snapshot(selected),
                    expires,
                ),
            )
            return {
                "token": token,
                "kind": kind,
                "ids": sorted(ids),
                "affected": {group: sorted(values) for group, values in selected.items()},
                "expires_at": datetime.fromtimestamp(expires, UTC).isoformat(),
                "expires_in_seconds": DELETE_TTL_SECONDS,
                "effect": "Selected records and dependent sessions/evidence are removed. All profile replay results are retired.",
                "consent": "Require explicit human approval in the host or supervised CLI; token possession is not consent.",
            }

    def confirm_delete(self, token: str) -> dict[str, Any]:
        if not isinstance(token, str) or not 20 <= len(token) <= 256:
            raise StoreError("Invalid deletion token.")
        with self._transaction(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM deletion_tokens WHERE token_hash=? AND profile=?", (_hash(token), self.profile)
            ).fetchone()
            if row is None or row["consumed"]:
                raise StoreError(
                    "Deletion token is invalid or already used. Prepare a new deletion.",
                    code="invalid_confirmation",
                )
            if time.time() >= row["expires_at"]:
                raise StoreError(
                    "Deletion token expired. Prepare deletion again and obtain new approval.",
                    code="expired_confirmation",
                )
            selected = self._selection(self._records(connection), row["kind"], json.loads(row["ids"]))
            if self._snapshot(selected) != row["snapshot"]:
                raise ConflictError(
                    "Deletion scope changed after preview. Prepare again and obtain new approval."
                )
            for kind, records in selected.items():
                connection.executemany(
                    "DELETE FROM records WHERE profile=? AND kind=? AND id=?",
                    [(self.profile, kind, identifier) for identifier in records],
                )
            # Deterministic request-key tombstones stop delayed retries. They
            # still confirm guessed profile/request-ID pairs (see Store's
            # contract). Erase payload digests and results so the tombstone
            # does not separately confirm the removed title or record fields.
            connection.execute(
                "UPDATE requests SET operation='',payload_hash='',result=NULL,retired=1 WHERE profile=?",
                (self.profile,),
            )
            # Every prior preview can contain selected IDs, including unused or
            # overlapping tokens. Invalidate and redact all of them atomically.
            connection.execute(
                "UPDATE deletion_tokens SET kind='',ids='[]',snapshot='',consumed=1 WHERE profile=?",
                (self.profile,),
            )
            result = {
                "deleted": {kind: len(records) for kind, records in selected.items()},
                "replay_results_retired": True,
            }
        # Best effort WAL truncation; physical erasure of backups or other
        # processes' snapshots is outside the active-product deletion contract.
        try:
            connection = self._connection()
            try:
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                connection.close()
        except sqlite3.Error:
            pass
        return result
