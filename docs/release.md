# Release process

The owner authorized public GitHub publication and a permissive license on 2026-11-16. Code, documentation and original bundled data use MIT. The repository is [kayammaori2-afk/repertorio](https://github.com/kayammaori2-afk/repertorio), with GitHub private vulnerability reporting as the security channel.

For each authorized release:

1. Start from a clean checkout; run `uv sync --locked`, `uv run python scripts/verify.py`, `uv run python scripts/inventory.py` and the dependency advisory scan.
2. Run `uv build` to build sdist and wheel. Install the wheel outside the source tree and run doctor, demo, evaluation and pilot. Verify bundled licenses and frozen input hashes.
3. Review documentation, privacy, original data rights, source/history scan and artifact contents. Preserve prior evidence and document any new freeze.
4. Commit the verified source. After publication to the authorized public repository, the manual Windows/Linux workflow can be dispatched on standard runners. It has no artifact/cache upload or automatic trigger and refuses private repositories.
5. Tag the exact reviewed commit, build the source ZIP from that tag, generate SHA-256 checksums, and publish the GitHub release with source ZIP, wheel, sdist and checksums. Verify the remote tag and uploaded asset hashes afterward.

The local dependency lock is authoritative for source installs. GitHub release assets are the supported v0.1.0 distribution; no PyPI upload, hosted service, remote tunnel or human study is implied. Run only authorized free CI; do not modify account budgets.

## Announcement

Repertorio is a local MCP server that lets your existing assistant consult repertoire and learning evidence across sessions. Version 0.1.0 includes corrections, import/export, constrained analogy selection and a reproducible synthetic evaluation. Try the demo and reproduce the checks. The benchmark has mixed, tie-sensitive results; student learning benefits remain unmeasured.
