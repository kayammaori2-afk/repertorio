"""Run the repository's local acceptance checks with an auditable exit status."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    checks = [
        ("lint", [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"]),
        ("types", [sys.executable, "-m", "mypy", "src/repertorio"]),
        ("tests", [sys.executable, "-m", "pytest", "-q"]),
        ("evaluation", [sys.executable, "-m", "repertorio", "evaluate", "--output", "evidence/evaluation"]),
        ("pilot", [sys.executable, "-m", "repertorio", "pilot", "--output", "evidence/pilot"]),
    ]
    results = []
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    for name, command in checks:
        run = subprocess.run(command, check=False, cwd=root, env=environment, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=300)
        (evidence / f"{name}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        results.append({"check": name, "command": command[2:], "exit_code": run.returncode,
                        "log": f"{name}.log"})
        print(f"{name}: {'PASS' if run.returncode == 0 else 'FAIL'}", flush=True)
    report = {"utc": datetime.now(UTC).isoformat(), "python": sys.version,
              "checks": results, "passed": all(row["exit_code"] == 0 for row in results)}
    (evidence / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
