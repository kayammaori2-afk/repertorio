# Independent release review

Claude Opus 5.5, static read-only review, 2026-11-16. Local path redacted. The implementing agent separately runs execution checks.

**Verdict: no blocking findings in the tree as it stands now. Conditionally ready**, pending the separate checks you said you'll run (tests, artifacts, remote settings, release assets).

**The tree changed while I was reviewing, and this matters.** My first reads found a real blocker. The v4 `frozen_manifest.json` listed `data/freeze_history_v3.json` inside its `sha256` map, but `input_hashes()` in `src/repertorio/evaluation.py:34` only hashes 8 files. So the comparison at `evaluation.py:307` always failed. At that point `evidence/tests.log` showed "2 failed, 129 passed", `evaluation.log` showed "Frozen evaluation inputs changed", and `verification.json` (18:10 UTC) showed `passed: false`.

When I re-read, all three had changed:
- The manifest now keeps the v3 hash in a separate `previous_manifest_sha256` field.
- `verification.json` (18:13 UTC) shows `passed: true`, and `tests.log` shows 131 passed.
- `evidence/evaluation/` is regenerated as freeze-v4 with the MIT rights text.
- The headline numbers match `evidence/publication/before-summary.json`: test split C−B −0.05030911, random-tie +0.15140236, overall +0.04673529.

So that blocker is fixed. Commit only the tree from after 18:13. The earlier failing `tests.log` contained `<user-home>/AppData/...` paths from tracebacks. Because `scripts/verify.py` writes into tracked `evidence/`, scan evidence for local paths right before committing.

**Confirmed by reading:**
- **License:** `LICENSE` is the standard MIT text. `pyproject.toml` has `license = "MIT"` and `license-files = ["LICENSE"]` on hatchling 1.27.0, and the sdist includes `LICENSE`. `local-checks.json` reports that the wheel's license text and metadata expression match.
- **Rights strings:** all 16 now read "MIT license". No current doc still says "pending" except where it is clearly marked historical (`verification.md` intro and line 43, `LICENSE-DECISION.md`).
- **Command accuracy:** every command in the README and the Portuguese quickstart matches the parser in `cli.py:287-351`.
- **CI:** `workflow_dispatch` only, `contents: read`, timeout 15 minutes, concurrency group, skipped on private repos, standard `ubuntu-latest`/`windows-latest` runners, no secrets, no artifact or cache upload.
- **Links:** all URLs consistently point to `kayammaori2-afk/repertorio`. Your other git identity and email don't appear in any of the public files I checked.
- **Credentials guidance:** tokens go to files under `PRIVATE_DIR` and are kept out of shell arguments. Only a hash is stored in the registry. No real credentials are in the examples.

**Worth fixing, not blocking:**
1. **Private profile could end up in the repo.** The README (`README.md:99-102`) and quickstart run `export --output profile.json` / `context.txt` from inside the clone. `.gitignore` covers neither file, nor `credentials.json` or `bearer.txt` if someone puts `PRIVATE_DIR` inside the repo. A contributor could commit a real profile by accident. Use `PRIVATE_DIR/` paths in those examples, or add ignore patterns.
2. **VS Code example contradicts the instructions.** `examples/vscode.mcp.json` hard-codes the Windows path `.venv/Scripts/python.exe` and leaves out `--db`. The README says to use an absolute private database path, and to use the same one in every assistant for continuity.
3. **Clean-install evidence is from the old wheel.** `evidence/clean-install.json` and the "byte-for-byte" claims in `verification.md` and `WORK_STATE.md` describe the pre-v4 wheel. `local-checks.json` doesn't record a fresh install outside the source tree. You said you'll redo this; `publication.md` should then point to the new record.
4. **CI pinning:** the actions are pinned to major tags (`@v4`/`@v5`), not commit SHAs. That's acceptable for manual-only CI.

**What I could not verify:**
- That the current manifest hashes are correct, or that tests pass. I can't run anything, so I'm relying on the 18:13 logs.
- Whether `uv==0.13.8` exists on PyPI.
- Wheel and sdist contents.
- Whether GitHub private vulnerability reporting is enabled. Until it is, the links in `SECURITY.md` and the README return 404. The Release link does too until v0.1.0 is published.
- Repository permissions, tag/asset hashes, and how the Actions runners actually behave.

This was a static AI review only, not a legal or security certification.
