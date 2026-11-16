"""Local installation, demonstration and supervised administration."""

from __future__ import annotations

import argparse
import asyncio
import copy
import csv
import hashlib
import importlib.metadata
import io
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path, PureWindowsPath
from typing import Any

from repertorio.server import (
    MAX_INPUT_BYTES,
    SCOPES,
    CredentialRegistry,
    StdioInputLimitError,
    serve_http,
    serve_stdio,
    validate_profile,
)
from repertorio.store import Store


def default_db() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "Repertorio" / "repertorio.sqlite3"


def restrict_windows_file(path: Path) -> None:
    system_root = PureWindowsPath(os.environ.get("SystemRoot") or r"C:\Windows")
    if not system_root.is_absolute():
        raise ValueError(
            "SystemRoot must be an absolute Windows directory; file permissions were not changed."
        )
    system32 = system_root / "System32"
    result = subprocess.run(
        [str(system32 / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        check=True,
    )
    # The username may use a Windows console code page. Only its ASCII SID is
    # required, so replacement decoding safely preserves that separate CSV field.
    try:
        rows = list(
            csv.reader(io.StringIO(result.stdout.decode("utf-8", errors="replace").strip()), strict=True)
        )
        if (
            len(rows) != 1
            or len(rows[0]) != 2
            or not re.fullmatch(r"S-1-[0-9]+(?:-[0-9]+){1,15}", rows[0][1])
        ):
            raise ValueError
        sid = rows[0][1]
    except (csv.Error, ValueError):
        raise ValueError(
            "Windows account SID could not be verified. Run System32/whoami.exe /user and repair the account lookup before retrying; file permissions were not changed."
        ) from None
    subprocess.run(
        [str(system32 / "icacls.exe"), str(path), "/inheritance:r", "/grant:r", f"*{sid}:(F)"],
        capture_output=True,
        check=True,
    )


def restrict_file(path: Path) -> None:
    if os.name == "nt":
        restrict_windows_file(path)
    else:
        path.chmod(0o600)


def write_private(path: Path, content: str, *, replace: bool = False) -> None:
    """Write privately, refuse accidental overwrite, atomically replace on request."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    target = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp") if replace else path
    fd = os.open(target, flags, 0o600)
    try:
        restrict_file(target)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            fd = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(target, path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        target.unlink(missing_ok=True)
        raise


def initialize_token(
    credentials_file: Path, token_file: Path, profile: str, scopes: list[str]
) -> dict[str, Any]:
    validate_profile(profile)
    if not scopes or not set(scopes) <= SCOPES or "read" not in scopes:
        raise ValueError("Credentials require read scope; optionally grant write and/or delete.")
    if credentials_file.resolve() == token_file.resolve():
        raise ValueError("Registry and token files must have different paths.")
    records = CredentialRegistry(credentials_file).read() if credentials_file.exists() else []
    if len(records) >= 100:
        raise ValueError("Registry has 100 credentials; revoke an unused credential first.")
    raw = secrets.token_urlsafe(48)
    identifier = uuid.uuid4().hex
    records.append(
        {
            "id": identifier,
            "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "profile": profile,
            "scopes": sorted(set(scopes)),
        }
    )
    write_private(token_file, raw + "\n")
    try:
        write_private(
            credentials_file,
            json.dumps({"version": 1, "credentials": records}, indent=2) + "\n",
            replace=credentials_file.exists(),
        )
    except BaseException:
        token_file.unlink(missing_ok=True)
        raise
    return {
        "credential_id": identifier,
        "credentials_file": str(credentials_file.resolve()),
        "token_file": str(token_file.resolve()),
        "profile": profile,
        "scopes": sorted(set(scopes)),
        "rotation": "Create another token file, update the authorized client, then remove the old credential ID from the registry. Revocation applies on the next request.",
    }


def read_input(path: Path) -> str:
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Import file exceeds one MiB.")
    return raw.decode("utf-8-sig")


async def run_demo(db: Path, profile: str) -> dict[str, Any]:
    """Real SDK client -> child stdio process -> persistent SQLite, twice."""
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client

    run_id = uuid.uuid4().hex
    transcript: list[dict[str, Any]] = []
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "repertorio", "--db", str(db.resolve()), "--profile", profile, "serve"],
    )

    async def call(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
        response = await session.call_tool(name, arguments)
        payload = response.structuredContent or json.loads(
            next(block.text for block in response.content if isinstance(block, types.TextContent))
        )
        transcript.append(
            {"tool": name, "arguments": copy.deepcopy(arguments), "result": copy.deepcopy(payload)}
        )
        if response.isError or not payload.get("ok"):
            raise ValueError("Demonstration operation failed; use an empty dedicated demo profile.")
        return payload["data"]

    async with stdio_client(parameters) as (reader, writer):  # noqa: SIM117 - dependent client lifecycle
        async with ClientSession(reader, writer) as session:
            initialized = await session.initialize()
            names = sorted(tool.name for tool in (await session.list_tools()).tools)
            current = await call(session, "get_profile", {})
            if current["repertoire"] or current["evidence"] or current["sessions"]:
                raise ValueError("Demo requires an empty dedicated profile; choose a new --profile.")
            item = {
                "id": "everyday:shopping",
                "title": "Synthetic weekly shopping",
                "kind": "experience",
                "status": "completed",
                "affinity": 4,
                "familiarity": 2,
                "progress": 100,
                "elements": ["budget", "prices", "alternatives"],
                "excluded": False,
                "source": "self_report",
            }
            saved = await call(session, "save_item", {"item": item, "request_id": uuid.uuid4().hex})
            before = await call(
                session,
                "prepare_context",
                {"concept": "opportunity_cost", "objective": "Explain the best forgone alternative"},
            )
            if not before["references"]:
                raise ValueError("Demo expected an eligible shopping reference.")
            await call(
                session,
                "record_session",
                {
                    "session": {
                        "id": f"demo-{run_id}",
                        "concept": "opportunity_cost",
                        "objective": "Synthetic transfer exercise",
                        "catalog_version": before["catalog_version"],
                        "policy_version": before["policy_version"],
                        "context_reference_ids": [reference["id"] for reference in before["references"]],
                        "repertoire_ids": [item["id"]],
                        "evidence_ids": [],
                        "client": "official-python-sdk-demo",
                        "model": None,
                        "usage": "delivered",
                        "usage_origin": "client_reported_delivery",
                    },
                    "request_id": uuid.uuid4().hex,
                },
            )
            await call(
                session,
                "record_evidence",
                {
                    "evidence": {
                        "id": f"demo-evidence-{run_id}",
                        "concept": "opportunity_cost",
                        "activity_id": "demo-transfer-1",
                        "activity_version": "1",
                        "help_received": "one_hint",
                        "result": "partial",
                        "origin": "tutor_assessment",
                        "assessor": "synthetic-demo",
                        "summary": "Synthetic evidence: named an alternative, but confused price and opportunity cost.",
                        "session_id": f"demo-{run_id}",
                    },
                    "request_id": uuid.uuid4().hex,
                },
            )

    async with stdio_client(parameters) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        resumed = await call(session, "get_profile", {})
        if resumed["repertoire"][0]["revision"] != saved["revision"]:
            raise ValueError("Demo reconnect did not recover the saved revision.")
        item["familiarity"] = 0
        corrected = await call(
            session,
            "save_item",
            {"item": item, "expected_revision": saved["revision"], "request_id": uuid.uuid4().hex},
        )
        after = await call(session, "prepare_context", {"concept": "opportunity_cost"})
        if after["references"]:
            raise ValueError("Demo correction did not remove the unconfirmed reference.")
    return {
        "synthetic": True,
        "transport": "stdio",
        "real_subprocesses": 2,
        "protocol_version": initialized.protocolVersion,
        "tools": names,
        "profile": profile,
        "database": str(db.resolve()),
        "persistent": True,
        "before_reference_count": len(before["references"]),
        "after_reference_count": len(after["references"]),
        "revision_after_correction": corrected["revision"],
        "interpretation": "Real protocol and persistence proof; no AI host or human learning study was performed.",
        "transcript": transcript,
    }


class ExactArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)


def parser() -> argparse.ArgumentParser:
    result = ExactArgumentParser(
        prog="repertorio", description="Portable local pedagogical context through MCP."
    )
    result.add_argument("--db", type=Path, default=default_db())
    result.add_argument("--profile", default="default")
    result.add_argument(
        "--allow-delete",
        action="store_true",
        help="Grant destructive operations to this local stdio process or CLI.",
    )
    commands = result.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start official MCP; stdio is the default.")
    serve.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument(
        "--credentials-file",
        type=Path,
        default=Path(os.environ["REPERTORIO_CREDENTIALS_FILE"])
        if os.environ.get("REPERTORIO_CREDENTIALS_FILE")
        else None,
    )
    token = commands.add_parser(
        "init-token", help="Generate a private token file and hash-only local HTTP registry."
    )
    token.add_argument("--credentials-file", type=Path, required=True)
    token.add_argument("--token-file", type=Path, required=True)
    token.add_argument("--scopes", nargs="+", choices=sorted(SCOPES), default=["read", "write"])
    commands.add_parser("doctor", help="Check SQLite access and installed dependency versions.")
    demo = commands.add_parser(
        "demo", help="Run a synthetic MCP demonstration in a temporary database unless --db is provided."
    )
    demo.add_argument("--output", type=Path)
    for name in ("evaluate", "pilot"):
        sub = commands.add_parser(name)
        sub.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser(
        "verify", help="Run the source distribution's verification gate; missing source is an error."
    )
    verify.add_argument("--repo", type=Path, default=Path.cwd())
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--format", choices=["json", "csv", "summary"], default="json")
    restore = commands.add_parser("import")
    restore.add_argument("--input", type=Path, required=True)
    restore.add_argument("--format", choices=["json", "csv"], default="json")
    restore.add_argument("--apply", action="store_true", help="Apply instead of previewing.")
    restore.add_argument(
        "--request-id",
        default=None,
        help="Opaque cryptographically random retry ID (UUID4); never include learner names, content or record IDs.",
    )
    delete = commands.add_parser(
        "delete", help="Supervised preview followed by a separate explicit confirmation command."
    )
    delete.add_argument("--kind", choices=["repertoire", "evidence", "sessions", "all"], default="repertoire")
    delete.add_argument("--id", action="append", default=[])
    delete.add_argument(
        "--confirmation", help="Prepared token; show the prior scope to the user before this step."
    )
    delete.add_argument(
        "--yes", action="store_true", help="Operator explicitly confirms the prepared deletion."
    )
    return result


def main(argv: list[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(raw_arguments)
    try:
        validate_profile(args.profile)
        if args.command == "serve":
            if args.transport == "stdio":
                asyncio.run(serve_stdio(args.db, args.profile, args.allow_delete))
            else:
                if args.credentials_file is None:
                    raise ValueError(
                        "HTTP requires --credentials-file or REPERTORIO_CREDENTIALS_FILE; run init-token."
                    )
                serve_http(args.db, args.credentials_file, args.host, args.port)
            return 0
        if args.command == "init-token":
            output = initialize_token(args.credentials_file, args.token_file, args.profile, args.scopes)
        elif args.command == "demo":
            if args.output and (args.output.exists() or args.output.is_symlink()):
                raise ValueError(
                    "Demo output already exists; choose an unused --output path before running the demonstration."
                )
            explicit_db = any(value == "--db" or value.startswith("--db=") for value in raw_arguments)
            if explicit_db:
                output = asyncio.run(run_demo(args.db, args.profile))
                output["temporary_database"] = False
            else:
                with tempfile.TemporaryDirectory(prefix="repertorio-demo-") as directory:
                    output = asyncio.run(run_demo(Path(directory) / "demo.sqlite3", args.profile))
                output["temporary_database"] = True
                output["database_disposition"] = (
                    "Temporary database removed after demonstrating process restart persistence."
                )
            if args.output:
                write_private(args.output, json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        elif args.command == "evaluate":
            from repertorio.evaluation import evaluate

            output = evaluate(args.output)
        elif args.command == "pilot":
            from repertorio.pilot import pilot

            output = pilot(args.output)
        elif args.command == "verify":
            script = args.repo.resolve() / "scripts" / "verify.py"
            if not script.is_file() or not (args.repo / "tests").is_dir():
                raise ValueError(
                    "Verification needs the source distribution with scripts/verify.py and tests. Extract it and pass --repo PATH; no checks were skipped or passed."
                )
            return subprocess.call([sys.executable, str(script)], cwd=args.repo.resolve())
        else:
            store = Store(args.db, args.profile)
            if args.command == "doctor":
                profile = store.get_profile()
                output = {
                    "ok": True,
                    "version": "0.1.0",
                    "python": sys.version.split()[0],
                    "mcp_sdk": importlib.metadata.version("mcp"),
                    "database": str(args.db.resolve()),
                    "profile": args.profile,
                    "schema_version": profile["schema_version"],
                    "repertoire_count": len(profile["repertoire"]),
                    "default_transport": "stdio",
                    "remote_oauth": False,
                    "delete_granted": args.allow_delete,
                }
            elif args.command == "export":
                payload = store.export_profile()
                if args.format == "json":
                    # Pretty-print overhead must not break restoration at the
                    # portable byte ceiling. Use --format summary for prose.
                    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                elif args.format == "csv":
                    content = store.export_csv()
                else:
                    profile = store.get_profile()
                    lines = [
                        "Repertorio manual snapshot",
                        "This text is data, not instructions. It does not update automatically.",
                        "",
                    ]
                    lines.extend(
                        f"- {json.dumps(item['title'], ensure_ascii=False)}: familiarity={item['familiarity']}, status={item['status']}, excluded={item['excluded']}"
                        for item in profile["repertoire"]
                    )
                    lines.extend(
                        [
                            "",
                            "Evidence is activity-specific, not proof of durable mastery.",
                            f"Recorded evidence: {len(profile['evidence'])}; sessions: {len(profile['sessions'])}.",
                        ]
                    )
                    lines.extend(
                        json.dumps(
                            {
                                key: record.get(key)
                                for key in (
                                    "concept",
                                    "activity_id",
                                    "activity_version",
                                    "help_received",
                                    "result",
                                    "origin",
                                    "assessor",
                                )
                            },
                            ensure_ascii=False,
                        )
                        for record in profile["evidence"]
                    )
                    content = "\n".join(lines) + "\n"
                write_private(args.output, content)
                output = {"exported": str(args.output.resolve()), "format": args.format, "snapshot": True}
            elif args.command == "import":
                content = read_input(args.input)
                request_id = args.request_id or f"cli-import-{uuid.uuid4().hex}"
                if args.format == "csv":
                    output = store.import_csv(content, request_id=request_id, dry_run=not args.apply)
                else:
                    output = store.import_profile(
                        json.loads(content), request_id=request_id, dry_run=not args.apply
                    )
            elif args.command == "delete":
                if not args.allow_delete:
                    raise ValueError(
                        "Deletion is disabled. The local operator must pass global --allow-delete."
                    )
                if args.confirmation:
                    if not args.yes:
                        raise ValueError(
                            "Review the prepared deletion scope and pass --yes to confirm it explicitly."
                        )
                    output = store.confirm_delete(args.confirmation)
                else:
                    if args.yes:
                        raise ValueError(
                            "First prepare deletion, then execute its confirmation token with --yes."
                        )
                    output = store.prepare_delete(args.kind, args.id)
            else:
                raise ValueError("Unknown command.")
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        return 0
    except (ValueError, OSError) as exc:
        # These local operator-facing errors never include credential values.
        print(f"Repertorio: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except ExceptionGroup as exc:
        if exc.subgroup(StdioInputLimitError) is not None:
            print(
                "Repertorio: stdio input exceeds two MiB; reconnect and send a smaller request.",
                file=sys.stderr,
            )
            return 2
        print("Repertorio: operation failed; run doctor. No success has been confirmed.", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - keep private data out of protocol/CLI exception traces
        print("Repertorio: operation failed; run doctor. No success has been confirmed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
