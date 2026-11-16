"""Inventory installed dependency metadata and inspect source distribution contents."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    rows = []
    for distribution in distributions():
        metadata = distribution.metadata
        rows.append({
            "name": metadata["Name"], "version": distribution.version,
            "license_expression": metadata.get("License-Expression"),
            "license": metadata.get("License"),
            "classifiers": [value for value in metadata.get_all("Classifier", [])
                            if value.startswith("License ::")],
        })
    (root / "evidence/dependency-licenses.json").write_text(
        json.dumps(sorted(rows, key=lambda row: row["name"].lower()), indent=2), encoding="utf-8"
    )
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                                    cwd=root, text=True).splitlines()
    patterns = [
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"(?:sk-proj-|ghp_)[A-Za-z0-9_-]{24,}"),
    ]
    issues = []
    manifest = []
    for name in sorted(set(paths)):
        path = root / name
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if path.suffix in {".db", ".sqlite", ".sqlite3"} or name.endswith(".env"):
            issues.append({"path": name, "issue": "private-state file"})
        if any(pattern.search(raw) for pattern in patterns):
            issues.append({"path": name, "issue": "possible credential, inspect privately"})
        if not name.startswith("evidence/"):
            manifest.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=root, text=True)
    blobs = 0
    for line in objects.splitlines():
        object_id, _, name = line.partition(" ")
        kind = subprocess.check_output(["git", "cat-file", "-t", object_id], cwd=root, text=True).strip()
        if kind != "blob":
            continue
        blobs += 1
        raw = subprocess.check_output(["git", "cat-file", "blob", object_id], cwd=root)
        if any(pattern.search(raw) for pattern in patterns) or name.endswith((".db", ".sqlite", ".sqlite3", ".env")):
            issues.append({"path": name, "object": object_id, "issue": "history requires private inspection"})
    report = {"scope": "current non-ignored publishing files including evidence, and all reachable Git blobs",
              "manifest_scope": "source files excluding generated evidence to avoid self-referential hashes",
              "limitations": "Pattern scan detects common credentials only; manual review is also required.",
              "history_blobs_scanned": blobs, "issues": issues, "files": manifest}
    (root / "evidence/source-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Inventoried {len(rows)} installed packages and {len(manifest)} source files; {len(issues)} issues")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
