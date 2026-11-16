from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path, PureWindowsPath

import pytest

from repertorio.cli import main, restrict_windows_file, run_demo
from repertorio.store import Store


@pytest.mark.parametrize("system_root", [None, "", r"C:\Windows", r"D:\Windows"])
def test_windows_permissions_use_absolute_tools_and_ascii_sid(tmp_path, monkeypatch, system_root):
    calls = []
    if system_root is None:
        monkeypatch.delenv("SystemRoot", raising=False)
    else:
        monkeypatch.setenv("SystemRoot", system_root)

    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        # Invalid UTF-8 in the account name must not corrupt the separate SID.
        return subprocess.CompletedProcess(arguments, 0, b'"COMPUTER\\Jos\xe9","S-1-5-21-1234"\r\n', b"")

    monkeypatch.setattr(subprocess, "run", run)
    restrict_windows_file(tmp_path / "private.token")
    assert len(calls) == 2
    root = PureWindowsPath(system_root or r"C:\Windows")
    assert calls[0][0][0] == str(root / "System32" / "whoami.exe")
    assert calls[1][0][0] == str(root / "System32" / "icacls.exe")
    assert calls[1][0][-1] == "*S-1-5-21-1234:(F)"
    assert all(PureWindowsPath(arguments[0]).is_absolute() for arguments, _ in calls)
    assert calls[0][1].get("text", False) is False


@pytest.mark.parametrize("system_root", ["Windows", r"C:Windows", r"\Windows"])
def test_windows_permissions_reject_relative_system_root(tmp_path, monkeypatch, system_root):
    monkeypatch.setenv("SystemRoot", system_root)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="absolute Windows directory"):
        restrict_windows_file(tmp_path / "private.token")
    assert not calls


@pytest.mark.parametrize(
    "output",
    [
        b"",
        b'"account"',
        b'"account","not-a-sid"',
        b'"account","S-1-5-x"',
        b'"unterminated',
        b'"one","S-1-5-21"\n"two","S-1-5-22"',
    ],
)
def test_windows_permissions_reject_malformed_sid_without_changing_acl(tmp_path, monkeypatch, output):
    calls = []
    monkeypatch.setenv("SystemRoot", r"C:\Windows")

    def run(arguments, **kwargs):
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, output, b"")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError, match="SID could not be verified"):
        restrict_windows_file(tmp_path / "private.token")
    assert len(calls) == 1


@pytest.mark.parametrize("arguments", [["--d", "unwanted.sqlite3", "demo"], ["demo", "--out", "out.json"]])
def test_cli_rejects_abbreviated_options_before_demo(tmp_path, monkeypatch, arguments):
    from repertorio import cli

    db = tmp_path / "default.sqlite3"
    monkeypatch.setattr(cli, "default_db", lambda: db)
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
    assert not db.exists()


def test_demo_existing_output_fails_before_database_is_populated(tmp_path, capsys):
    output = tmp_path / "existing.json"
    output.write_text("preserved")
    db = tmp_path / "demo.sqlite3"
    assert main(["--db", str(db), "demo", "--output", str(output)]) == 2
    assert "output already exists" in capsys.readouterr().err
    assert output.read_text() == "preserved"
    assert not db.exists()


def test_init_token_is_private_hash_only_and_no_secret_output(tmp_path, capsys):
    registry, token = tmp_path / "credentials.json", tmp_path / "client.token"
    args = [
        "--profile",
        "alice",
        "init-token",
        "--credentials-file",
        str(registry),
        "--token-file",
        str(token),
    ]
    assert main(args) == 0
    captured = capsys.readouterr()
    raw = token.read_text().strip()
    assert len(raw) >= 48
    assert raw not in captured.out + captured.err + registry.read_text()
    assert json.loads(captured.out)["scopes"] == ["read", "write"]
    assert main(args) == 2  # never silently replace a credential file
    assert token.read_text().strip() == raw


def test_bare_demo_is_temporary_and_preserves_default_profile(tmp_path, monkeypatch, capsys):
    db = tmp_path / "real-profile.sqlite3"
    from repertorio import cli

    monkeypatch.setattr(cli, "default_db", lambda: db)
    assert main(["demo"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["temporary_database"] is True
    assert not Path(result["database"]).exists()
    assert not db.exists()
    store = Store(db, "default")
    store.save_item({"id": "real-item", "title": "Existing operator profile"}, "seed-real")
    before = store.export_profile()
    assert main(["demo"]) == 0
    capsys.readouterr()
    assert store.export_profile() == before


def test_token_creation_requires_read_scope(tmp_path, capsys):
    registry, token = tmp_path / "credentials.json", tmp_path / "client.token"
    assert (
        main(
            [
                "init-token",
                "--credentials-file",
                str(registry),
                "--token-file",
                str(token),
                "--scopes",
                "write",
            ]
        )
        == 2
    )
    assert "require read" in capsys.readouterr().err
    assert not registry.exists() and not token.exists()


async def test_demo_real_mcp_persistence(tmp_path):
    result = await run_demo(tmp_path / "demo.sqlite3", "demo-profile")
    assert result["real_subprocesses"] == 2
    assert result["before_reference_count"] > 0
    assert result["after_reference_count"] == 0
    assert result["protocol_version"] == "2025-11-25"
    assert any(step["tool"] == "record_evidence" for step in result["transcript"])
    saves = [step for step in result["transcript"] if step["tool"] == "save_item"]
    assert saves[0]["arguments"]["item"]["familiarity"] == 2
    assert saves[1]["arguments"]["item"]["familiarity"] == 0
    requests = [
        step["arguments"]["request_id"] for step in result["transcript"] if "request_id" in step["arguments"]
    ]
    assert len(requests) == len(set(requests))
    assert all(uuid.UUID(value).version == 4 for value in requests)
    assert (tmp_path / "demo.sqlite3").is_file()


def test_cli_doctor_export_import_delete_and_verify_failure(tmp_path, capsys):
    db = tmp_path / "admin.sqlite3"
    prefix = ["--db", str(db), "--profile", "admin"]
    assert main(prefix + ["doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    snapshot = tmp_path / "profile.json"
    assert main(prefix + ["export", "--output", str(snapshot)]) == 0
    capsys.readouterr()
    assert main(prefix + ["import", "--input", str(snapshot)]) == 0
    assert json.loads(capsys.readouterr().out)
    assert main(prefix + ["delete", "--kind", "all"]) == 2
    capsys.readouterr()
    assert main(prefix + ["--allow-delete", "delete", "--kind", "all"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert main(prefix + ["--allow-delete", "delete", "--confirmation", plan["token"]]) == 2
    capsys.readouterr()
    assert main(prefix + ["--allow-delete", "delete", "--confirmation", plan["token"], "--yes"]) == 0
    capsys.readouterr()
    assert main(["verify", "--repo", str(tmp_path)]) == 2
    assert "no checks were skipped or passed" in capsys.readouterr().err


def test_cli_http_requires_credentials_and_never_accepts_token_argument(tmp_path):
    for arguments in (["serve", "--transport", "http"], ["serve", "--token", "synthetic-nonsecret"]):
        result = subprocess.run(
            [sys.executable, "-m", "repertorio", "--db", str(tmp_path / "db.sqlite3"), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode != 0
        assert result.stdout == ""
    assert not (tmp_path / "db.sqlite3").exists()


def test_cli_verify_propagates_failure(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts" / "verify.py").write_text("raise SystemExit(7)\n")
    assert main(["verify", "--repo", str(tmp_path)]) == 7


def test_cli_rejects_large_import_before_database_change(tmp_path, capsys):
    source = tmp_path / "oversized.json"
    source.write_text("x" * 1_048_577)
    assert main(["--db", str(tmp_path / "db.sqlite3"), "import", "--input", str(source)]) == 2
    assert "one MiB" in capsys.readouterr().err
