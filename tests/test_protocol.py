"""Real subprocess MCP acceptance and local HTTP boundary rejection proofs."""

from __future__ import annotations

import asyncio
import copy
import json
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from repertorio.cli import initialize_token, main
from repertorio.models import Evidence
from repertorio.server import (
    MAX_INPUT_BYTES,
    MAX_REQUEST_BYTES,
    REQUEST_ID_GUIDANCE,
    TOOLS,
    CredentialRegistry,
    LocalHTTPBoundary,
    http_app,
    input_schema,
)
from repertorio.store import Store


def test_mutation_request_ids_describe_random_opaque_retries():
    tools = {"save_item", "record_evidence", "record_session", "import_profile"}
    for name in tools:
        spec = TOOLS[name]
        assert REQUEST_ID_GUIDANCE in spec[2]
        schema = input_schema(name, spec[0])
        assert schema["properties"]["request_id"]["description"] == REQUEST_ID_GUIDANCE
    deletion_description = TOOLS["confirm_delete"][2]
    assert "Opaque anti-replay request markers remain" in deletion_description
    assert "external backups, exports and host transcripts" in deletion_description


def sample_item():
    return {
        "id": "everyday:shopping",
        "title": "PRIVATE_SYNTHETIC_CANARY_76254",
        "kind": "experience",
        "status": "completed",
        "affinity": 5,
        "familiarity": 2,
        "progress": 100,
        "elements": ["budget", "prices", "alternatives"],
        "excluded": False,
        "source": "self_report",
    }


@asynccontextmanager
async def stdio_session(db: Path, profile="alice", allow_delete=False):
    args = ["-m", "repertorio", "--db", str(db), "--profile", profile]
    if allow_delete:
        args.append("--allow-delete")
    args.append("serve")
    params = StdioServerParameters(command=sys.executable, args=args)
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
        initialized = await session.initialize()
        assert initialized.protocolVersion == "2025-11-25"
        yield session


@asynccontextmanager
async def http_session(url: str, token: str):
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as client:  # noqa: SIM117
        async with streamable_http_client(url, http_client=client) as (reader, writer, session_id):
            async with ClientSession(reader, writer) as session:
                initialized = await session.initialize()
                assert initialized.protocolVersion == "2025-11-25"
                assert session_id() is None  # application continuity is stored in SQLite
                yield session


async def call(session, name, arguments=None, *, error=None):
    result = await session.call_tool(name, arguments or {})
    assert result.structuredContent is not None
    assert json.loads(result.content[0].text) == result.structuredContent
    payload = result.structuredContent
    if error:
        assert result.isError
        assert payload["error"]["code"] == error
        return payload["error"]
    assert not result.isError, payload
    assert payload["ok"] is True
    return payload["data"]


@contextmanager
def running_http(tmp_path: Path, db: Path, registry: Path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log_path = tmp_path / f"server-{port}.stderr"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "repertorio",
                "--db",
                str(db),
                "serve",
                "--transport",
                "http",
                "--port",
                str(port),
                "--credentials-file",
                str(registry),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=log,
        )
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            deadline = time.monotonic() + 20
            with httpx.Client(timeout=0.25) as client:
                while True:
                    if process.poll() is not None:
                        pytest.fail(f"HTTP server exited {process.returncode}: {log_path.read_text()}")
                    try:
                        if client.get(url).status_code == 401:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        pytest.fail("HTTP server failed to start")
                    time.sleep(0.05)
            yield url, process, log_path
        finally:
            process.terminate()
            stdout, _ = process.communicate(timeout=10)
            assert stdout == b""


@pytest.fixture
def credentials(tmp_path):
    registry = tmp_path / "credentials.json"
    values = {}
    for key, profile, scopes in [
        ("alice", "alice", ["read", "write", "delete"]),
        ("bob", "bob", ["read", "write", "delete"]),
        ("reader", "alice", ["read"]),
    ]:
        path = tmp_path / f"{key}.token"
        initialize_token(registry, path, profile, scopes)
        values[key] = path.read_text().strip()
    return registry, values


@pytest.mark.asyncio
async def test_continuity_real_stdio_http_restart_isolation(tmp_path, credentials):
    db = tmp_path / "continuity.sqlite3"
    registry, tokens = credentials
    async with stdio_session(db) as session:
        listed = await session.list_tools()
        assert len(listed.tools) == 9
        tools = {tool.name: tool for tool in listed.tools}
        assert tools["get_profile"].annotations.readOnlyHint
        assert tools["confirm_delete"].annotations.destructiveHint
        assert "profile" not in tools["save_item"].inputSchema["properties"]
        item_schema = tools["save_item"].inputSchema["properties"]["item"]
        assert item_schema["properties"]["familiarity"]["maximum"] == 3
        assert item_schema["additionalProperties"] is False
        saved = await call(session, "save_item", {"item": sample_item(), "request_id": "create-1"})
        duplicate = await call(session, "save_item", {"item": sample_item(), "request_id": "create-1"})
        assert duplicate == saved
        before = await call(session, "prepare_context", {"concept": "opportunity_cost"})
        assert before["references"]
        await call(
            session,
            "record_session",
            {
                "session": {
                    "id": "lesson-1",
                    "objective": "opportunity cost transfer",
                    "concept": "opportunity_cost",
                    "catalog_version": before["catalog_version"],
                    "context_reference_ids": [r["id"] for r in before["references"]],
                    "repertoire_ids": [saved["id"]],
                    "evidence_ids": [],
                    "usage": "delivered",
                    "usage_origin": "client_reported_delivery",
                },
                "request_id": "session-1",
            },
        )
        await call(
            session,
            "record_evidence",
            {
                "evidence": {
                    "id": "evidence-1",
                    "concept": "opportunity_cost",
                    "activity_id": "transfer-1",
                    "activity_version": "1",
                    "help_received": "one_hint",
                    "result": "partial",
                    "origin": "tutor_assessment",
                    "assessor": "synthetic-tutor",
                    "session_id": "lesson-1",
                },
                "request_id": "evidence-1",
            },
        )
        await call(session, "prepare_delete", {"kind": "all", "ids": []}, error="insufficient_scope")
    with running_http(tmp_path, db, registry) as (url, _, log_path):
        async with http_session(url, tokens["alice"]) as session:
            resumed = await call(session, "get_profile")
            assert resumed["repertoire"][0] == saved
            assert len(resumed["evidence"]) == len(resumed["sessions"]) == 1
            corrected = await call(
                session,
                "save_item",
                {
                    "item": {"id": saved["id"], "familiarity": 0},
                    "expected_revision": saved["revision"],
                    "request_id": "correct-1",
                },
            )
            assert corrected["revision"] == saved["revision"] + 1
            after = await call(session, "prepare_context", {"concept": "opportunity_cost"})
            assert not after["references"]
            assert after["fallback"]
            exported = await call(session, "export_profile")
        async with http_session(url, tokens["bob"]) as session:
            assert not (await call(session, "get_profile"))["repertoire"]
            await call(
                session,
                "save_item",
                {
                    "item": {"id": saved["id"], "familiarity": 2},
                    "expected_revision": saved["revision"],
                    "request_id": "foreign",
                },
                error="conflict",
            )
        assert sample_item()["title"] not in log_path.read_text()
        assert all(value not in log_path.read_text() for value in tokens.values())
    with running_http(tmp_path, db, registry) as (url, _, _):
        async with http_session(url, tokens["alice"]) as session:
            assert (await call(session, "get_profile"))["repertoire"][0] == corrected
            assert (await call(session, "export_profile"))["repertoire"] == exported["repertoire"]
        async with http_session(url, tokens["bob"]) as session:
            assert not (await call(session, "get_profile"))["sessions"]


@pytest.mark.asyncio
async def test_http_auth_scopes_rejection_limits_revocation(tmp_path, credentials):
    db = tmp_path / "security.sqlite3"
    registry, tokens = credentials
    with running_http(tmp_path, db, registry) as (url, _, log_path):
        async with httpx.AsyncClient() as client:
            assert (await client.get(url)).status_code == 401
            assert (
                await client.post(url, headers={"Authorization": "Bearer invalid-token"})
            ).status_code == 401
            headers = {"Authorization": f"Bearer {tokens['alice']}"}
            assert (await client.get(url, headers={**headers, "Host": "attacker.invalid"})).status_code == 403
            assert (
                await client.get(url, headers={**headers, "Origin": "https://attacker.invalid"})
            ).status_code == 403
            assert (await client.get(url, headers={"Mcp-Session-Id": "stolen-session"})).status_code == 401
            huge = b"x" * (MAX_REQUEST_BYTES + 1)
            assert (await client.post(url, headers=headers, content=huge)).status_code == 413

            async def chunks():
                yield huge[:600_000]
                yield huge[600_000:]

            assert (
                await client.post(
                    url, headers={**headers, "Content-Type": "application/json"}, content=chunks()
                )
            ).status_code == 413
        async with http_session(url, tokens["reader"]) as session:
            assert not (await call(session, "get_profile"))["repertoire"]
            await call(
                session,
                "save_item",
                {"item": sample_item(), "request_id": "forbidden"},
                error="insufficient_scope",
            )
            await call(session, "prepare_delete", {"kind": "all", "ids": []}, error="insufficient_scope")
        async with http_session(url, tokens["alice"]) as session:
            await call(session, "get_profile", {"profile": "bob"}, error="invalid_input")
            nested = {"v": "data"}
            for _ in range(14):
                nested = {"v": nested}
            await call(session, "save_item", {"item": nested, "request_id": "nested"}, error="invalid_input")
            await call(
                session,
                "import_profile",
                {"payload": {"path": "C:/private/secret"}, "request_id": "path"},
                error="invalid_input",
            )
            assert not (await call(session, "get_profile"))["repertoire"]
        data = json.loads(registry.read_text())
        data["credentials"] = [record for record in data["credentials"] if record["profile"] != "bob"]
        registry.write_text(json.dumps(data))
        async with httpx.AsyncClient() as client:
            assert (
                await client.get(url, headers={"Authorization": f"Bearer {tokens['bob']}"})
            ).status_code == 401
            assert (
                await client.get(url, headers={"Authorization": f"Bearer {tokens['alice']}"})
            ).status_code != 401
        assert "secret" not in log_path.read_text()


@pytest.mark.asyncio
async def test_delete_contract_real_http_and_stdio(tmp_path, credentials):
    db = tmp_path / "delete.sqlite3"
    registry, tokens = credentials
    async with stdio_session(db, allow_delete=True) as session:
        await call(session, "save_item", {"item": sample_item(), "request_id": "seed"})
        plan = await call(session, "prepare_delete", {"kind": "repertoire", "ids": [sample_item()["id"]]})
    with running_http(tmp_path, db, registry) as (url, _, _):
        async with http_session(url, tokens["bob"]) as session:
            result = await session.call_tool("confirm_delete", {"token": plan["token"]})
            assert result.isError
        async with http_session(url, tokens["alice"]) as session:
            result = await call(session, "confirm_delete", {"token": plan["token"]})
            assert result["deleted"]["repertoire"] == 1
            assert not (await call(session, "get_profile"))["repertoire"]
            repeated = await session.call_tool("confirm_delete", {"token": plan["token"]})
            assert repeated.isError
    async with stdio_session(db) as session:
        assert not (await call(session, "get_profile"))["repertoire"]


def test_insecure_http_startup_refused(tmp_path, credentials):
    registry, _ = credentials
    for host in ("0.0.0.0", "192.168.1.1", "::", "localhost", "attacker.invalid"):
        with pytest.raises(ValueError, match="loopback"):
            http_app(tmp_path / "unsafe.sqlite3", registry, host)
    with pytest.raises(ValueError, match="Credential registry"):
        http_app(tmp_path / "unsafe.sqlite3", tmp_path / "missing.json")
    invalid = json.loads(registry.read_text())
    invalid["credentials"][0]["scopes"] = ["write"]
    invalid_registry = tmp_path / "write-only.json"
    invalid_registry.write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="Credential registry"):
        http_app(tmp_path / "unsafe.sqlite3", invalid_registry)
    assert not (tmp_path / "unsafe.sqlite3").exists()


@pytest.mark.asyncio
async def test_near_limit_export_restores_over_real_http_and_late_invalid_record_is_atomic(
    tmp_path, credentials
):
    registry, tokens = credentials
    stamp = "2026-01-01T00:00:00+00:00"
    records = [
        Evidence.model_validate(
            {
                "id": f"e-{index:03}",
                "concept": "probability",
                "activity_id": "synthetic-limit-fixture",
                "activity_version": "1",
                "help_received": "none",
                "result": "partial",
                "origin": "self_report",
                "assessor": "synthetic",
                "summary": "",
                "created_at": stamp,
                "updated_at": stamp,
            }
        ).model_dump(mode="json")
        for index in range(700)
    ]
    profile = {"schema_version": 1, "repertoire": [], "evidence": records, "sessions": []}
    serialized = json.dumps(profile, separators=(",", ":"))
    remaining = MAX_INPUT_BYTES - 32 - len(serialized.encode())
    for record in records:
        length = min(1200, remaining)
        record["summary"] = "x" * length
        remaining -= length
    assert remaining == 0
    assert len(json.dumps(profile, separators=(",", ":")).encode()) == MAX_INPUT_BYTES - 32
    arguments = {"payload": profile, "request_id": "large-roundtrip", "dry_run": False}
    assert len(json.dumps(arguments).encode()) > MAX_INPUT_BYTES
    assert len(json.dumps(arguments).encode()) < MAX_REQUEST_BYTES
    with running_http(tmp_path, tmp_path / "limit.sqlite3", registry) as (url, _, log_path):
        async with http_session(url, tokens["alice"]) as session:
            imported = await call(session, "import_profile", arguments)
            assert imported["committed"]
            exported = await call(session, "export_profile")
            assert exported == profile
        async with http_session(url, tokens["bob"]) as session:
            invalid = copy.deepcopy(exported)
            invalid["evidence"][-1]["origin"] = "verified"
            error = await call(
                session,
                "import_profile",
                {
                    "payload": invalid,
                    "request_id": "late-invalid",
                    "dry_run": False,
                },
                error="invalid_input",
            )
            assert "xxxxx" not in error["message"]
            assert not (await call(session, "get_profile"))["evidence"]
            await call(
                session,
                "import_profile",
                {
                    "payload": exported,
                    "request_id": "valid-restoration",
                    "dry_run": False,
                },
            )
            assert await call(session, "export_profile") == exported
        assert "xxxxx" not in log_path.read_text()
    snapshot = tmp_path / "full-profile.json"
    assert (
        main(
            [
                "--db",
                str(tmp_path / "limit.sqlite3"),
                "--profile",
                "alice",
                "export",
                "--output",
                str(snapshot),
            ]
        )
        == 0
    )
    assert snapshot.stat().st_size <= MAX_INPUT_BYTES
    restored_db = tmp_path / "restored-cli.sqlite3"
    assert (
        main(
            [
                "--db",
                str(restored_db),
                "--profile",
                "cli-restored",
                "import",
                "--input",
                str(snapshot),
                "--apply",
            ]
        )
        == 0
    )
    assert Store(restored_db, "cli-restored").export_profile() == exported


@pytest.mark.asyncio
async def test_http_timeout_and_concurrency_bound(tmp_path, credentials, monkeypatch):
    registry, tokens = credentials
    import repertorio.server as server_module

    monkeypatch.setattr(server_module, "REQUEST_TIMEOUT", 0.1)

    async def blocked_app(scope, receive, send):
        await asyncio.sleep(5)

    boundary = LocalHTTPBoundary(blocked_app, CredentialRegistry(registry), "127.0.0.1", 8765)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=boundary),
        base_url="http://127.0.0.1:8765",
        headers={"Authorization": f"Bearer {tokens['alice']}"},
    ) as client:
        requests = [client.get("/mcp") for _ in range(12)]
        results = await asyncio.gather(*requests)
    assert sum(result.status_code == 408 for result in results) == 8
    assert sum(result.status_code == 429 for result in results) == 4


def test_stdio_stdout_is_protocol_only_and_bounded(tmp_path):
    args = [sys.executable, "-m", "repertorio", "--db", str(tmp_path / "stdio.sqlite3"), "serve"]
    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "raw-probe", "version": "1"},
                    },
                }
            )
            + "\n"
        )
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        assert response["id"] == 1 and response["result"]["protocolVersion"] == "2025-11-25"
        process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n')
        process.stdin.flush()
        assert len(json.loads(process.stdout.readline())["result"]["tools"]) == 9
        process.stdin.close()
        process.wait(timeout=10)
        assert process.stdout.read() == ""
        assert process.stderr.read() == ""
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    oversized = subprocess.run(
        args,
        check=False,
        input=("x" * (MAX_REQUEST_BYTES + 1)) + "\n",
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert oversized.returncode != 0
    assert oversized.stdout == ""
    assert len(oversized.stderr) < 300
    assert "two MiB; reconnect" in oversized.stderr
