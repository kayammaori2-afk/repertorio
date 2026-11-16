# Repertorio execution state

Requested execution uses GPT-6 Astra, Extra High and Standard. The primary chat reports Astra. Implementation agents are explicitly configured as Astra/xhigh, with no premium-speed request. Speed for the current chat cannot be changed by these tools.

The initial specification is docs/specification.txt. On 2026-11-16 the owner subsequently authorized selecting a permissive license and publishing to GitHub with release v0.1.0. MIT is selected for original code/docs/data; the verified target is kayammaori2-afk/repertorio.

## Final local candidate

Persistent core, both transports, CLI, selector, offline evaluation and synthetic pilot are implemented. The final integrated check passed 131 tests, lint and types. Claude Code and Codex exercised continuity on the same synthetic profile; Inspector discovery/read also passed. Sanitized evidence is in evidence/.

SQLite schema4 persists catalog-reference dependencies for deletion. The final independent static reviews closed the material code and methodology findings under the documented boundaries. The original fixed-order test contrast remains negative; symmetric tie sensitivity changes its sign. No human efficacy evidence exists.

Wheel and sdist are built, with the wheel built from sdist. Installation outside the source tree passed doctor, the two-process demo, evaluation and pilot. All eight deterministic evaluation artifacts and four pilot artifacts matched byte-for-byte. Locked runtime dependencies matched. evidence/clean-install.json records the artifacts/hashes for the final packaging pass. evidence/source-inventory.json records the source/history scan. The source archive's external release manifest records its final commit and checksums without a circular self-hash.

Commands from this directory: `uv sync --locked`; `uv run python scripts/verify.py`; `uv build`; `uv run python scripts/inventory.py`; `uv run pip-audit --format json --output evidence/dependency-audit.json`. Clean install must be outside this source tree. docs/verification.md records scope and limits; final logs take precedence over older review observations.

Publication preparation: README, Portuguese usage guide, MIT metadata/text, repository links, private reporting channel and manual-only public-repository CI are prepared. The catalog rights-only change is frozen as v4 with previous hashes retained. Publication checks are recorded in evidence/publication and docs/publication.md. Next: repeat local verification and clean package installation, independent release review, create/push public repository, run free standard Windows/Linux CI, tag exact verified head and publish checked artifacts. Current remote outcomes must be verified before claiming release success.

Research still requires specialist review before any recruitment. Remote ChatGPT, a hosted service and PyPI publication are outside this release.

## Ownership

- Root owns packaging, lockfile, docs except evaluation/pilot docs, integration, release evidence.
- Storage agent owns models.py, store.py, test_store.py.
- MCP agent owns server.py, cli.py, __main__.py, test_protocol.py, test_cli.py.
- Evaluation agent owns selection.py, evaluation.py, pilot.py, data/, test_selection.py, test_evaluation.py, evaluation and pilot docs.

## Shared contract

See CONTRACT.md. No UI. Python with official MCP SDK verified from installed sources. No cloud operations or human participants.
