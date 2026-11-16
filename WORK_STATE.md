# Repertorio execution state

## v0.2.0 reviewed release — 2026-11-16

The owner requested improved experience/evaluation, autonomous local validation and a prepared user pilot. Root owns this follow-up; prior per-file agent ownership below is historical. Branch: feature/v0.2.0-pilot-ready. The v0.1 release is not changed by this work.

Implemented generated host snippets, bilingual read-only learning_options, prospective five-arm tutor evaluation with blinded ratings, and empty pilot materials/readiness/usability analysis. Frozen selector/evaluator/pilot inputs remain unchanged. No human observations or external pedagogical review. A real Codex first-use run exposed omitted experience status; corrected guidance was re-exercised on a fresh synthetic profile. TOML paths with non-BMP Unicode are regression-tested.

The owner explicitly authorized closing the pending Claude review, repairs, merge of PR #1 and publication of v0.2.0. After the subscription reset, Claude Opus 5.5 completed independent static review and two closeouts; all findings were repaired or bounded explicitly and the final verdict has no code blocker. Local source and Python 3.11 package checks passed 175 tests with three local symlink skips. Final published commit, CI and exact artifact checks belong to the release manifest/receipt, not the earlier candidate files. No human research results or expert approval exist. See docs/v0.2.0.md and evidence/v0.2/.

Requested execution uses GPT-6 Astra, Extra High and Standard. The primary chat reports Astra. Implementation agents are explicitly configured as Astra/xhigh, with no premium-speed request. Speed for the current chat cannot be changed by these tools.

The initial specification is docs/specification.txt. On 2026-11-16 the owner subsequently authorized selecting a permissive license and publishing to GitHub with release v0.1.0. MIT is selected for original code/docs/data; the verified target is kayammaori2-afk/repertorio.

## Historical v0.1 local candidate

Persistent core, both transports, CLI, selector, offline evaluation and synthetic pilot are implemented. The final integrated check passed 131 tests, lint and types. Claude Code and Codex exercised continuity on the same synthetic profile; Inspector discovery/read also passed. Sanitized evidence is in evidence/.

SQLite schema4 persists catalog-reference dependencies for deletion. The final independent static reviews closed the material code and methodology findings under the documented boundaries. The original fixed-order test contrast remains negative; symmetric tie sensitivity changes its sign. No human efficacy evidence exists.

Wheel and sdist are built, with the wheel built from sdist. Installation outside the source tree passed doctor, the two-process demo, evaluation and pilot. All eight deterministic evaluation artifacts and four pilot artifacts matched byte-for-byte. Locked runtime dependencies matched. evidence/clean-install.json records the artifacts/hashes for the final packaging pass. evidence/source-inventory.json records the source/history scan. The source archive's external release manifest records its final commit and checksums without a circular self-hash.

Commands from this directory: `uv sync --locked`; `uv run python scripts/verify.py`; `uv build`; `uv run python scripts/inventory.py`; `uv run pip-audit --format json --output evidence/dependency-audit.json`. Clean install must be outside this source tree. docs/verification.md records scope and limits; final logs take precedence over older review observations.

Publication state: MIT source is public at https://github.com/kayammaori2-afk/repertorio. GitHub private vulnerability reporting is enabled. Manual Windows/Linux CI run 43927397744 passed; public-clone demo and exact evaluation reproduction passed. The original development history is preserved only on local-development-history; public main begins with the reviewed snapshot and noreply author identity. Tag v0.1.0 and its final uploaded assets are verified through the external release receipt/manifest; do not infer a public asset from a local filename.

Research still requires specialist review before any recruitment. Remote ChatGPT, a hosted service and PyPI publication are outside this release.

## Ownership

- Root owns packaging, lockfile, docs except evaluation/pilot docs, integration, release evidence.
- Storage agent owns models.py, store.py, test_store.py.
- MCP agent owns server.py, cli.py, __main__.py, test_protocol.py, test_cli.py.
- Evaluation agent owns selection.py, evaluation.py, pilot.py, data/, test_selection.py, test_evaluation.py, evaluation and pilot docs.

## Shared contract

See CONTRACT.md. No UI. Python with official MCP SDK verified from installed sources. No cloud operations or human participants.
