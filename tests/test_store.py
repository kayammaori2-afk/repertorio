"""Storage acceptance tests use only disposable synthetic profiles."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest

from repertorio.models import MAX_INPUT_BYTES, bounded_json
from repertorio.selection import catalog, prepare_context
from repertorio.store import DB_VERSION, ConflictError, Store, StoreError


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "synthetic.db", "alice")


def item(identifier: str = "everyday:shopping", **overrides: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": "A synthetic grocery budget",
        "kind": "experience",
        "status": "completed",
        "familiarity": 2,
        "affinity": 4,
        "elements": ["budget", "prices", "alternatives"],
        **overrides,
    }


def evidence(identifier: str = "e1", **overrides: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "concept": "opportunity_cost",
        "activity_id": "transfer:budget",
        "activity_version": "1",
        "help_received": "one hint",
        "result": "partly correct",
        "origin": "tutor_assessment",
        "assessor": "synthetic tutor",
        "summary": "Compared the next-best alternative.",
        **overrides,
    }


def graph(store: Store) -> dict[str, Any]:
    saved = store.save_item(
        item(
            spoiler_limit=40.5,
            progress=55,
            external_ids={"example": "42"},
            language="pt-BR",
            tags=["budget"],
            edition="original",
        ),
        "item",
    )
    store.record_session(
        {
            "id": "s1",
            "objective": "Compare alternatives",
            "concept": "opportunity_cost",
            "catalog_version": "catalog-v1",
            "policy_version": "selector-v1",
            "repertoire_ids": [saved["id"]],
            "context_reference_ids": ["ref:budget"],
            "client": None,
            "model": None,
        },
        "session",
    )
    store.record_evidence(evidence(session_id="s1", occurred_at="2026-11-16T09:00:00+00:00"), "evidence")
    return store.export_profile()


def test_commit_restart_isolation_partial_update_and_noop(store: Store) -> None:
    first = store.save_item(item(), "save")
    restarted = Store(store.path, "alice")
    second = restarted.save_item({"id": first["id"], "familiarity": 0}, "correction", 1)
    assert second["revision"] == 2
    assert second["elements"] == first["elements"]
    assert second["affinity"] == first["affinity"]
    assert second["created_at"] == first["created_at"]
    assert second["updated_at"] >= first["updated_at"]
    assert restarted.save_item({"id": first["id"], "familiarity": 0}, "noop", 2) == second
    assert Store(store.path, "bob").get_profile() == {
        "schema_version": 1,
        "repertoire": [],
        "evidence": [],
        "sessions": [],
    }


def test_replay_original_result_even_after_later_update(store: Store) -> None:
    first = store.save_item(item(), "save")
    second = store.save_item({"id": first["id"], "familiarity": 0}, "correct", 1)
    assert store.save_item(item(), "save") == first
    assert store.get_profile()["repertoire"] == [second]
    with pytest.raises(ConflictError, match="different content"):
        store.save_item(item(title="Changed"), "save")
    with pytest.raises(ConflictError, match="different content"):
        store.record_evidence(evidence(), "save")
    # The same operation key in another identity is a separate namespace.
    assert Store(store.path, "bob").save_item(item(), "save")["revision"] == 1


def test_expected_revision_cannot_be_omitted_or_stale(store: Store) -> None:
    saved = store.save_item(item(), "save")
    for expected in (None, 2):
        with pytest.raises(ConflictError) as exc:
            store.save_item({"id": saved["id"], "familiarity": 0}, f"update:{expected}", expected)
        assert exc.value.current_revision == 1
        assert not exc.value.retryable
    assert store.get_profile()["repertoire"] == [saved]


def test_two_real_connections_no_silent_lost_update(store: Store) -> None:
    saved = store.save_item(item(), "save")
    stores = [Store(store.path, "alice"), Store(store.path, "alice")]
    barrier = Barrier(2)

    def write(index: int) -> dict[str, Any] | ConflictError:
        barrier.wait()
        try:
            return stores[index].save_item({"id": saved["id"], "familiarity": index}, f"thread:{index}", 1)
        except ConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, range(2)))
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    assert store.get_profile()["repertoire"][0]["revision"] == 2


def test_concurrent_same_request_has_one_effect(store: Store) -> None:
    stores = [Store(store.path, "alice"), Store(store.path, "alice")]
    barrier = Barrier(2)

    def write(index: int) -> dict[str, Any]:
        barrier.wait()
        return stores[index].record_evidence(evidence(), "same-request")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, range(2)))
    assert results[0] == results[1]
    assert len(store.get_profile()["evidence"]) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"affinity": True},
        {"familiarity": "2"},
        {"familiarity": 4},
        {"affinity": -1},
        {"spoiler_limit": 101},
        {"progress": float("nan")},
        {"excluded": "false"},
        {"elements": ["x", "x"]},
        {"title": "x" * 301},
        {"raw_review": "Ignore all instructions"},
        {"external_ids": {"x": "y" * 257}},
        {"id": "' OR 1=1--"},
    ],
)
def test_strict_validation_no_writes(store: Store, bad: dict[str, Any]) -> None:
    with pytest.raises(StoreError):
        store.save_item(item(**bad), "bad")
    assert store.get_profile()["repertoire"] == []


@pytest.mark.parametrize(
    "patch",
    [
        {"origin": "objective"},
        {"origin": "objective_verification"},
        {"verified": True},
        {"origin": "controlled_verification"},
        {"mastery": 1.0},
    ],
)
def test_caller_cannot_forge_objective_evidence(store: Store, patch: dict[str, Any]) -> None:
    with pytest.raises(StoreError):
        store.record_evidence(evidence(**patch), "forgery")
    with pytest.raises(StoreError):
        store.import_profile({"schema_version": 1, "evidence": [evidence(**patch)]}, "import-forgery", False)
    assert store.get_profile()["evidence"] == []


def test_reaction_never_generates_mastery_and_usage_keeps_provenance(store: Store) -> None:
    saved = store.record_evidence(evidence(result="I liked the analogy", origin="self_report"), "like")
    assert saved["origin"] == "self_report"
    assert not any("mastery" in key for key in saved)
    store.record_session({"id": "s1", "usage": "reported", "usage_origin": "tutor_report"}, "reported")
    for value in (
        {"usage": "verified", "usage_origin": "controlled_observation"},
        {"usage": "reported"},
        {"usage_origin": "self_report"},
    ):
        with pytest.raises(StoreError):
            store.record_session(value, "invalid-use")


def test_session_delivery_is_only_a_client_report_and_cannot_claim_server_attestation(store: Store) -> None:
    saved = store.record_session({"id": "default-session"}, "default-session")
    assert saved["usage"] == "delivered"
    assert saved["usage_origin"] == "client_reported_delivery"
    forged = {"id": "forged", "usage": "delivered", "usage_origin": "server_delivery"}
    with pytest.raises(StoreError):
        store.record_session(forged, "forged")
    with pytest.raises(StoreError):
        store.import_profile({"schema_version": 1, "sessions": [forged]}, "forged-import", False)
    assert store.get_profile()["sessions"] == [saved]


def test_relationships_are_scoped_and_missing_links_rollback(store: Store) -> None:
    graph(store)
    bob = Store(store.path, "bob")
    with pytest.raises(StoreError, match="authenticated profile"):
        bob.record_evidence(evidence(session_id="s1"), "cross-profile")
    with pytest.raises(StoreError, match="authenticated profile"):
        bob.record_session({"id": "s2", "repertoire_ids": ["everyday:shopping"]}, "cross-session")
    assert not bob.get_profile()["evidence"]
    assert not bob.get_profile()["sessions"]
    with pytest.raises(StoreError):
        store.import_profile(
            {
                "schema_version": 1,
                "repertoire": [item("new")],
                "evidence": [evidence("e2", session_id="missing")],
            },
            "bad-links",
            False,
        )
    assert len(store.get_profile()["repertoire"]) == 1


def test_full_export_restore_preserves_all_fields_relations_and_provenance(
    store: Store, tmp_path: Path
) -> None:
    exported = graph(store)
    other = Store(tmp_path / "portable.db", "new-identity")
    preview = other.import_profile(exported, "restore")
    assert preview["dry_run"] and not preview["committed"]
    assert other.get_profile()["repertoire"] == []
    applied = other.import_profile(exported, "restore", False)
    assert applied["committed"]
    assert other.export_profile() == exported
    assert other.import_profile(exported, "restore", False) == applied
    repeated = other.import_profile(exported, "again", False)
    assert all(count["added"] == 0 for count in repeated["counts"].values())
    assert other.export_profile() == exported


def test_import_sparse_repeat_is_noop_and_older_import_never_overwrites_correction(store: Store) -> None:
    payload = {"schema_version": 1, "repertoire": [item()]}
    store.import_profile(payload, "first", False)
    original = store.export_profile()
    store.import_profile(payload, "second", False)
    assert store.export_profile() == original
    store.save_item({"id": "everyday:shopping", "familiarity": 0}, "correct", 1)
    preview = store.import_profile(payload, "third")
    assert preview["conflicts"][0]["current_revision"] == 2
    with pytest.raises(ConflictError):
        store.import_profile(payload, "third", False)
    assert store.get_profile()["repertoire"][0]["familiarity"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"schema_version": "1"},
        {"schema_version": 1.0},
        {"repertoire": []},
        {"schema_version": 1, "repertoire": [item(), item()]},
        {"schema_version": 1, "repertoire": [item("a"), item("b", familiarity=9)]},
        {"schema_version": 1, "profile": "victim"},
    ],
)
def test_import_invalid_version_duplicates_and_records_atomic(store: Store, payload: dict[str, Any]) -> None:
    with pytest.raises(StoreError):
        store.import_profile(payload, "invalid", False)
    assert store.get_profile()["repertoire"] == []


def test_import_conflict_never_partially_commits_other_new_records(store: Store) -> None:
    saved = store.save_item(item("existing"), "save")
    payload = {"schema_version": 1, "repertoire": [item("new"), item("existing", title="Conflict")]}
    assert len(store.import_profile(payload, "merge")["conflicts"]) == 1
    with pytest.raises(ConflictError):
        store.import_profile(payload, "merge", False)
    assert store.get_profile()["repertoire"] == [saved]


def test_actual_database_failure_rolls_back_composite_import_and_replay(store: Store) -> None:
    with sqlite3.connect(store.path) as connection:
        connection.execute("""CREATE TRIGGER controlled_failure BEFORE INSERT ON records
            WHEN NEW.id='fail' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END""")
    payload = {"schema_version": 1, "repertoire": [item("success"), item("fail")]}
    with pytest.raises(StoreError) as exc:
        store.import_profile(payload, "atomic", False)
    assert exc.value.retryable
    assert "synthetic failure" not in str(exc.value)
    assert store.get_profile()["repertoire"] == []
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT count(*) FROM requests").fetchone()[0] == 0
        connection.execute("DROP TRIGGER controlled_failure")
    assert store.import_profile(payload, "atomic", False)["committed"]


def test_csv_export_import_roundtrip_and_invalid_rows(store: Store, tmp_path: Path) -> None:
    graph(store)
    text = store.export_csv()
    other = Store(tmp_path / "csv.db", "bob")
    assert other.import_csv(text, "csv")["counts"]["repertoire"]["added"] == 1
    other.import_csv(text, "csv", False)
    assert other.get_profile()["repertoire"] == store.get_profile()["repertoire"]
    before = other.get_profile()
    invalid = [
        "id,title\nx,x,extra\n",
        "id,id,title\nx,x,x\n",
        "id,title\nx\n",
        "id,title,familiarity\nx,x,two\n",
        "id,title,excluded\nx,x,yes\n",
        "id,title,raw_review\nx,x,instructions\n",
        "id,title,elements\nx,x,[broken\n",
    ]
    for text in invalid:
        with pytest.raises(StoreError):
            other.import_csv(text, "invalid", False)
        assert other.get_profile() == before


def test_limits_depth_bytes_record_count_and_types(store: Store) -> None:
    nested: Any = {}
    for _ in range(14):
        nested = {"next": nested}
    cyclic: list[Any] = []
    cyclic.append(cyclic)
    for value in (nested, cyclic, {"x": "x" * MAX_INPUT_BYTES}, {"x": object()}, {1: "bad"}):
        with pytest.raises(ValueError):
            bounded_json(value)
    with pytest.raises(StoreError):
        store.import_profile(
            {"schema_version": 1, "repertoire": [item(str(i)) for i in range(1001)]}, "many", False
        )
    assert store.get_profile()["repertoire"] == []


def test_profile_growth_cannot_produce_unrestorable_export(
    store: Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A reduced limit exercises the boundary with small fixtures. The same
    # production check enforces the actual 1 MiB portable ceiling.
    monkeypatch.setattr("repertorio.models.MAX_INPUT_BYTES", 2500)
    for index in range(20):
        try:
            store.save_item(item(f"item:{index}"), f"save:{index}")
        except StoreError as exc:
            assert "portable size limit" in str(exc)
            break
    else:
        pytest.fail("Profile size guard never rejected growth")
    exported = store.export_profile()
    assert 1 < len(exported["repertoire"]) < 20
    assert len(bounded_json(exported).encode("utf-8")) <= 2500
    destination = Store(tmp_path / "bounded-restore.db", "bob")
    destination.import_profile(exported, "restore", False)
    assert destination.export_profile() == exported


def test_delete_bound_to_profile_revision_expiry_and_single_use(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = store.save_item(item(), "save")
    token = store.prepare_delete("repertoire", [saved["id"]])["token"]
    bob = Store(store.path, "bob")
    with pytest.raises(StoreError, match="invalid"):
        bob.confirm_delete(token)
    store.save_item({"id": saved["id"], "familiarity": 0}, "change", 1)
    with pytest.raises(ConflictError, match="changed"):
        store.confirm_delete(token)
    token = store.prepare_delete("repertoire", [saved["id"]])["token"]
    with sqlite3.connect(store.path) as connection:
        expiry = connection.execute("SELECT max(expires_at) FROM deletion_tokens").fetchone()[0]
    with monkeypatch.context() as patch:
        patch.setattr("repertorio.store.time.time", lambda: expiry + 1)
        with pytest.raises(StoreError, match="expired"):
            store.confirm_delete(token)
    token = store.prepare_delete("repertoire", [saved["id"]])["token"]
    # Restart must preserve confirmations.
    assert Store(store.path, "alice").confirm_delete(token)["deleted"]["repertoire"] == 1
    with pytest.raises(StoreError, match="already used"):
        store.confirm_delete(token)


def test_delete_removes_derived_and_replay_payloads_without_affecting_other_identity(store: Store) -> None:
    exported = graph(store)
    bob = Store(store.path, "bob")
    bob.import_profile(exported, "restore", False)
    preview = store.prepare_delete("repertoire", ["everyday:shopping"])
    assert preview["affected"] == {
        "repertoire": ["everyday:shopping"],
        "sessions": ["s1"],
        "evidence": ["e1"],
    }
    assert store.confirm_delete(preview["token"])["deleted"] == {
        "repertoire": 1,
        "evidence": 1,
        "sessions": 1,
    }
    assert all(not store.get_profile()[kind] for kind in ("repertoire", "sessions", "evidence"))
    assert bob.export_profile() == exported
    with sqlite3.connect(store.path) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM requests WHERE profile='alice' AND result IS NOT NULL"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM requests WHERE profile='bob' AND result IS NOT NULL"
            ).fetchone()[0]
            == 1
        )
    with pytest.raises(StoreError) as exc:
        store.record_evidence(evidence(session_id="s1", occurred_at="2026-11-16T09:00:00+00:00"), "evidence")
    assert exc.value.code == "deleted_result"
    assert store.get_profile()["evidence"] == []


def test_deletion_redacts_plaintext_and_content_digests_but_retains_request_markers(store: Store) -> None:
    identifier = "private:synthetic-record-to-erase"
    title = "SYNTHETIC-IDENTIFIABLE-TITLE-TO-ERASE"
    # Deliberately violates the random/nonsemantic-ID guidance to expose the
    # residual: plaintext is removed, but this request ID remains guessable.
    store.save_item(item(identifier, title=title), identifier)
    first = store.prepare_delete("repertoire", [identifier])
    second = store.prepare_delete("all", [])
    with sqlite3.connect(store.path) as connection:
        payload_hash = connection.execute("SELECT payload_hash FROM requests").fetchone()[0]
        snapshot = connection.execute("SELECT snapshot FROM deletion_tokens LIMIT 1").fetchone()[0]
    assert len(snapshot) == 64 and identifier not in snapshot
    store.confirm_delete(second["token"])
    with sqlite3.connect(store.path) as connection:
        dump = "\n".join(connection.iterdump())
        for secret in (identifier, title, payload_hash, snapshot):
            assert secret not in dump
        guessed_request_key = hashlib.sha256(
            json.dumps(["alice", identifier], separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert connection.execute(
            "SELECT retired FROM requests WHERE profile=? AND request_id=?",
            ("alice", guessed_request_key),
        ).fetchone() == (1,)
        assert (
            connection.execute(
                "SELECT count(*) FROM deletion_tokens WHERE snapshot!='' OR ids!='[]'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM requests WHERE payload_hash!='' OR result IS NOT NULL"
            ).fetchone()[0]
            == 0
        )
    with pytest.raises(StoreError, match="already used"):
        store.confirm_delete(first["token"])
    with pytest.raises(StoreError) as exc:
        store.save_item(item(identifier, title=title), identifier)
    assert exc.value.code == "deleted_result"
    # Both payload guesses confirm only that the request ID is retired; neither
    # distinguishes the deleted payload's title from a different guess.
    with pytest.raises(StoreError) as exc:
        store.save_item(item(identifier, title="Different guess"), identifier)
    assert exc.value.code == "deleted_result"
    # The same caller-provided key in a different profile is independent.
    bob = Store(store.path, "bob")
    assert bob.save_item(item("bob:unrelated"), identifier)["id"] == "bob:unrelated"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM requests WHERE profile=? AND request_id=?",
            ("bob", guessed_request_key),
        ).fetchone() == (0,)


def test_expired_previews_are_pruned_on_reopen_and_next_preview(store: Store) -> None:
    store.save_item(item(), "item")
    store.prepare_delete("all", [])
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE deletion_tokens SET expires_at=0")
    Store(store.path, "alice")
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT count(*) FROM deletion_tokens").fetchone()[0] == 0
    store.prepare_delete("all", [])
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE deletion_tokens SET expires_at=0")
    store.prepare_delete("all", [])
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT count(*) FROM deletion_tokens").fetchone()[0] == 1


def test_deletion_detects_new_derived_record_and_all_profile_growth(store: Store) -> None:
    saved = store.save_item(item(), "save")
    token = store.prepare_delete("repertoire", [saved["id"]])["token"]
    store.record_session({"id": "new", "repertoire_ids": [saved["id"]]}, "derived")
    with pytest.raises(ConflictError, match="changed"):
        store.confirm_delete(token)
    token = store.prepare_delete("all", [])["token"]
    store.save_item(item("new-item"), "new-item")
    with pytest.raises(ConflictError, match="changed"):
        store.confirm_delete(token)


@pytest.mark.parametrize(
    ("kind", "ids"),
    [
        ("all", ["x"]),
        ("repertoire", []),
        ("unknown", []),
        ("repertoire", ["x", "x"]),
        ("repertoire", [{"bad": "value"}]),
        ("repertoire", "x"),
    ],
)
def test_invalid_deletion_selection(store: Store, kind: str, ids: Any) -> None:
    with pytest.raises(StoreError):
        store.prepare_delete(kind, ids)


def test_deletion_selected_evidence_does_not_remove_unrelated_item(store: Store) -> None:
    graph(store)
    token = store.prepare_delete("evidence", ["e1"])["token"]
    result = store.confirm_delete(token)
    assert result["deleted"] == {"repertoire": 0, "sessions": 0, "evidence": 1}
    assert len(store.get_profile()["repertoire"]) == 1


def test_delete_evidence_removes_sessions_that_embed_its_reference(store: Store) -> None:
    store.record_evidence(evidence(), "evidence")
    store.record_session({"id": "s1", "evidence_ids": ["e1"]}, "session")
    preview = store.prepare_delete("evidence", ["e1"])
    assert preview["affected"]["sessions"] == ["s1"]
    assert store.confirm_delete(preview["token"])["deleted"] == {
        "repertoire": 0,
        "evidence": 1,
        "sessions": 1,
    }


def test_v1_migration_preserves_records_and_repeated_initialization(tmp_path: Path) -> None:
    path = tmp_path / "v1.db"
    original = {
        **item(),
        "revision": 1,
        "created_at": "2026-11-16T09:00:00+00:00",
        "updated_at": "2026-11-16T09:00:00+00:00",
    }
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE records(profile TEXT NOT NULL, kind TEXT NOT NULL,
            id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(profile,kind,id))""")
        connection.execute(
            "INSERT INTO records VALUES(?,?,?,?,?)",
            ("alice", "repertoire", original["id"], 1, json.dumps(original)),
        )
        connection.execute("PRAGMA user_version=1")
    migrated = Store(path, "alice")
    expected = migrated.export_profile()
    for key, value in original.items():
        assert expected["repertoire"][0][key] == value
    assert expected["repertoire"][0]["tags"] == []
    for _ in range(2):
        assert Store(path, "alice").export_profile() == expected
    assert migrated.import_profile(expected, "self-roundtrip", False)["counts"]["repertoire"] == {
        "added": 0,
        "unchanged": 1,
    }
    assert migrated.save_item({"id": original["id"], "familiarity": 0}, "edit-migrated", 1)["revision"] == 2
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == DB_VERSION
        assert connection.execute("SELECT count(*) FROM deletion_tokens").fetchone()[0] == 0


def test_v2_migration_normalizes_missing_dates_and_unattested_delivery(tmp_path: Path) -> None:
    path = tmp_path / "v2.db"
    initial = Store(path, "alice")
    initial.save_item(item(), "old-record-id")
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE records SET body=?", (json.dumps(item()),))
        connection.execute(
            "INSERT INTO records VALUES(?,?,?,?,?)",
            (
                "alice",
                "sessions",
                "old-session",
                1,
                json.dumps({"id": "old-session", "usage_origin": "server_delivery"}),
            ),
        )
        connection.execute("UPDATE requests SET request_id='old-record-id'")
        connection.execute("PRAGMA user_version=2")
    migrated = Store(path, "alice")
    exported = migrated.export_profile()
    assert exported["repertoire"][0]["created_at"] is not None
    assert exported["repertoire"][0]["updated_at"] is not None
    assert exported["sessions"][0]["usage_origin"] == "client_reported_delivery"
    assert not migrated.import_profile(exported, "normalize-reimport", False)["conflicts"]
    assert (
        migrated.save_item({"id": "everyday:shopping", "affinity": 1}, "edit-normalized", 1)["revision"] == 2
    )
    with pytest.raises(StoreError) as exc:
        migrated.save_item(item(), "old-record-id")
    assert exc.value.code == "deleted_result"


def test_revision_limit_rejects_change_without_corrupting_export(store: Store, tmp_path: Path) -> None:
    maximum = 2_147_483_647
    store.import_profile({"schema_version": 1, "repertoire": [item(revision=maximum)]}, "max-revision", False)
    before = store.export_profile()
    with pytest.raises(StoreError) as exc:
        store.save_item({"id": "everyday:shopping", "familiarity": 0}, "overflow", maximum)
    assert exc.value.code == "revision_limit"
    assert store.export_profile() == before
    assert store.save_item({"id": "everyday:shopping"}, "noop-at-limit", maximum)["revision"] == maximum
    restored = Store(tmp_path / "max-restored.db", "bob")
    restored.import_profile(before, "restore", False)
    assert restored.export_profile() == before


def test_schema_migration_failure_rolls_back_and_future_schema_rejected(tmp_path: Path) -> None:
    broken = tmp_path / "broken.db"
    with sqlite3.connect(broken) as connection:
        connection.execute("CREATE TABLE requests(x)")
    with pytest.raises(StoreError):
        Store(broken, "alice")
    with sqlite3.connect(broken) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            connection.execute("SELECT count(*) FROM sqlite_master WHERE name='records'").fetchone()[0] == 0
        )
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(StoreError, match="newer"):
        Store(broken, "alice")


def test_invalid_legacy_record_has_actionable_error_and_preserves_original_database(store: Store) -> None:
    store.save_item(item(), "legacy-request")
    invalid_body = json.dumps(item(familiarity="not-an-integer"))
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE records SET body=?", (invalid_body,))
        connection.execute("PRAGMA user_version=2")
        original_requests = connection.execute("SELECT * FROM requests").fetchall()
    with pytest.raises(StoreError) as exc:
        Store(store.path, "alice")
    assert exc.value.code == "migration_invalid_record"
    assert "rolled back" in str(exc.value) and "backup" in str(exc.value)
    assert "not-an-integer" not in str(exc.value)
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT body FROM records").fetchone()[0] == invalid_body
        assert connection.execute("SELECT * FROM requests").fetchall() == original_requests


def test_sqlite_backup_restore_on_disposable_database(store: Store, tmp_path: Path) -> None:
    expected = graph(store)
    path = tmp_path / "restored.db"
    with sqlite3.connect(store.path) as source, sqlite3.connect(path) as destination:
        source.backup(destination)
    restored = Store(path, "alice")
    assert restored.export_profile() == expected
    restored.confirm_delete(restored.prepare_delete("all", [])["token"])
    assert store.export_profile() == expected


def test_concurrent_database_initialization(tmp_path: Path) -> None:
    path = tmp_path / "concurrent.db"
    barrier = Barrier(2)

    def start(profile: str) -> dict[str, Any]:
        barrier.wait()
        return Store(path, profile).get_profile()

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(start, ["alice", "bob"]))
    assert values[0] == values[1]


def test_context_only_session_is_bound_deleted_with_evidence_and_cannot_restore_usage(store: Store) -> None:
    store.save_item(item(), "item")
    original_session = {
        "id": "context-only",
        "usage": "reported",
        "usage_origin": "self_report",
        "context_reference_ids": ["oc-shopping"],
    }
    saved = store.record_session(original_session, "context-session")
    assert saved["repertoire_ids"] == ["everyday:shopping"]
    assert saved["catalog_version"] == catalog()["version"]
    store.record_evidence(evidence(session_id="context-only"), "linked-evidence")
    before = prepare_context(store.get_profile(), "opportunity_cost")
    assert before["references"][0]["reason"]["components"]["documented_prior_use"] == 1
    preview = store.prepare_delete("repertoire", ["everyday:shopping"])
    assert preview["affected"] == {
        "repertoire": ["everyday:shopping"],
        "sessions": ["context-only"],
        "evidence": ["e1"],
    }
    assert store.confirm_delete(preview["token"])["deleted"] == {
        "repertoire": 1,
        "sessions": 1,
        "evidence": 1,
    }
    assert store.get_profile()["sessions"] == []
    assert store.get_profile()["evidence"] == []
    with pytest.raises(StoreError) as exc:
        store.record_session(original_session, "context-session")
    assert exc.value.code == "deleted_result"
    with sqlite3.connect(store.path) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM requests WHERE result IS NOT NULL OR payload_hash!=''"
            ).fetchone()[0]
            == 0
        )
    store.save_item(item(), "new-explicit-registration")
    after = prepare_context(store.get_profile(), "opportunity_cost")
    assert after["references"][0]["reason"]["components"]["documented_prior_use"] == 0


def test_import_binds_context_references_and_reimport_is_noop(store: Store) -> None:
    payload = {
        "schema_version": 1,
        "repertoire": [item()],
        "sessions": [{"id": "imported-context", "context_reference_ids": ["oc-shopping"]}],
    }
    assert store.import_profile(payload, "import-context", False)["committed"]
    exported = store.export_profile()
    assert exported["sessions"][0]["repertoire_ids"] == ["everyday:shopping"]
    assert exported["sessions"][0]["catalog_version"] == catalog()["version"]
    assert not store.import_profile(payload, "repeat-context", False)["conflicts"]
    assert store.export_profile() == exported


def test_persisted_context_links_survive_catalog_removal_and_portable_restore(
    store: Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.save_item(item(), "item")
    store.record_session({"id": "old-context", "context_reference_ids": ["oc-shopping"]}, "session")
    exported = store.export_profile()
    monkeypatch.setattr("repertorio.store.catalog", lambda: {"version": "future-version", "references": []})
    restored = Store(tmp_path / "future-catalog.db", "bob")
    restored.import_profile(exported, "restore", False)
    assert restored.export_profile() == exported
    for instance in (store, restored):
        preview = instance.prepare_delete("repertoire", ["everyday:shopping"])
        assert preview["affected"]["sessions"] == ["old-context"]
        instance.confirm_delete(preview["token"])
        assert instance.get_profile()["sessions"] == []


@pytest.mark.parametrize(
    "session",
    [
        {"id": "unknown-reference", "context_reference_ids": ["missing-reference"]},
        {
            "id": "unknown-version",
            "catalog_version": "historical-unknown",
            "context_reference_ids": ["oc-shopping"],
        },
    ],
)
def test_unknown_context_requires_explicit_repertoire_links_atomically(
    store: Store, session: dict[str, Any]
) -> None:
    store.save_item(item(), "item")
    with pytest.raises(StoreError, match="explicit repertoire_ids"):
        store.record_session(session, "unsupported-context")
    with pytest.raises(StoreError, match="explicit repertoire_ids"):
        store.import_profile(
            {"schema_version": 1, "repertoire": [item("would-be-new")], "sessions": [session]},
            "unsupported-import",
            False,
        )
    assert len(store.get_profile()["repertoire"]) == 1
    assert store.get_profile()["sessions"] == []
    bound = store.record_session({**session, "repertoire_ids": ["everyday:shopping"]}, "declared-links")
    assert bound["repertoire_ids"] == ["everyday:shopping"]
    assert store.prepare_delete("repertoire", ["everyday:shopping"])["affected"]["sessions"] == [
        session["id"]
    ]


def test_current_catalog_closure_covers_legacy_context_only_records(store: Store) -> None:
    store.save_item(item(), "item")
    saved = store.record_session(
        {"id": "legacy-context", "context_reference_ids": ["oc-shopping"]}, "session"
    )
    # Simulate a pre-fix record without reopening/migrating, to exercise the
    # deletion fallback separately from new-write normalization.
    saved["repertoire_ids"] = []
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE records SET body=? WHERE kind='sessions'", (json.dumps(saved),))
    preview = store.prepare_delete("repertoire", ["everyday:shopping"])
    assert preview["affected"]["sessions"] == ["legacy-context"]
    store.confirm_delete(preview["token"])
    assert store.get_profile()["sessions"] == []


def test_v3_migration_backfills_catalog_links_and_retires_old_receipts(store: Store) -> None:
    store.save_item(item(), "item")
    original = {"id": "old-context", "context_reference_ids": ["oc-shopping"]}
    saved = store.record_session(original, "session")
    saved["repertoire_ids"] = []
    saved["catalog_version"] = "unknown"
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE records SET body=? WHERE kind='sessions'", (json.dumps(saved),))
        connection.execute("PRAGMA user_version=3")
    migrated = Store(store.path, "alice")
    assert migrated.get_profile()["sessions"][0]["repertoire_ids"] == ["everyday:shopping"]
    assert migrated.get_profile()["sessions"][0]["catalog_version"] == catalog()["version"]
    assert migrated.import_profile(migrated.export_profile(), "self-reimport", False)["committed"]
    with pytest.raises(StoreError) as exc:
        migrated.record_session(original, "session")
    assert exc.value.code == "deleted_result"
    assert migrated.prepare_delete("repertoire", ["everyday:shopping"])["affected"]["sessions"] == [
        "old-context"
    ]


def test_v3_unresolved_context_migration_fails_without_partial_changes(store: Store) -> None:
    saved = store.record_session({"id": "old-unknown"}, "session")
    saved["context_reference_ids"] = ["unresolvable-old-reference"]
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE records SET body=? WHERE kind='sessions'", (json.dumps(saved),))
        connection.execute("PRAGMA user_version=3")
    with pytest.raises(StoreError) as exc:
        Store(store.path, "alice")
    assert exc.value.code == "migration_invalid_record"
    assert "repertoire links" in str(exc.value)
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert json.loads(connection.execute("SELECT body FROM records").fetchone()[0]) == saved
