# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

**Verdict:** one material defect remains open. The deletion fix only partly solves the first must-fix item: request IDs are now stored as a hash anyone can recompute, so a guess about a deleted ID can still be confirmed. The other eight listed items are fixed in the code. I found no new must-fix bugs in them. I read the code and tests only and ran nothing. `evidence/tests.log` reports "99 passed in 27.37s", but I can't confirm that log matches the current code.

## Unresolved material defect

**Deleted data can still be confirmed through the stored request IDs (`store.py:240`, `store.py:643-648`)**
- **What happens:** the request key stored in `requests` is a plain SHA-256 of the profile name and the caller's request ID, with no secret. Deletion blanks `operation`, `payload_hash` and `result`, but this key stays forever.
- **Why it matters:** anyone who can read the database can guess a profile and request ID, hash them and look for a match. If a client puts a record ID in its request IDs, this confirms the deleted ID. That is the same kind of leak as the payload hash, which the fix erased.
  - The comment at `store.py:643-644` says digests "must not confirm guesses about deleted data". That promise doesn't hold here.
- **Why the test misses it:** `test_deletion_erases_ids_titles_payload_hashes_and_all_overlapping_previews` (`tests/test_store.py:438`) uses the record ID as the request ID, the exact case described above. It only checks that the raw ID, title, payload hash and snapshot are gone, not this key.
  - Through the tools, a caller can also probe the same profile: a reused request ID returns `deleted_result`, a new one doesn't. That is a lower risk, because only the profile's own credential can do it.
- **Fix options:**
  - Require random request IDs, such as UUIDs. This is the strongest fix, but it is a breaking change.
  - Or state in the `save_item`, `record_*` and `import_profile` tool descriptions and in the docs that request IDs must be random and carry no meaning. Then reword the comment and `docs/data.md:30`.
  - Either way, add a test that `requests.request_id` doesn't contain `sha256(_json([profile, request_id]))` for a meaningful request ID, or drop that claim.
  - A secret-keyed hash would only help if the key were kept outside the database.

## Verdict per item

| Item | Verdict |
|---|---|
| Deletion tables retained IDs and payload hashes | **Partly fixed.** Snapshots are now one hash and per-ID lists are gone. All of the profile's previews are invalidated and redacted on confirm, expired previews are pruned, and payload hashes and results are blanked. The request-key gap above remains. |
| Bare demo wrote into the real default profile | **Fixed.** Without `--db`, the demo runs in a temporary directory (`cli.py:337-347`). With `--db`, it still refuses a profile that isn't empty. An abbreviated `--d` falls into the safe temporary path. The test covers both an empty and a populated real database. |
| `server_delivery` naming | **Fixed.** The only allowed value is now `client_reported_delivery`, and delivery requires that origin. Migration rewrites old values, and new or imported `server_delivery` values are rejected. Both are tested. |
| Revision overflow | **Fixed.** Edits are refused at the cap with `revision_limit`, a no-op save at the cap still works, and export and restore at the cap are tested. |
| Sparse v1 migration | **Fixed.** Schema v3 runs every v1/v2 record through the model, fills in missing dates, and checks the ID and revision against the row. It runs in one transaction and rolls back on failure. Re-importing a migrated profile is a no-op, and edits work. |
| Windows bare-name utility lookup | **Fixed**, with a minor gap: `cli.py:44` turns an empty `SystemRoot` into the relative path `System32`, which brings back the current-directory lookup. Use `os.environ.get("SystemRoot") or r"C:\Windows"` and check the path is absolute. Only someone who controls the parent environment can trigger this. |
| Mutation credentials without read | **Fixed.** `read` is required both when tokens are created (`cli.py:88`) and when the registry is loaded (`server.py:374`). Both are tested. |
| Undeclared direct dependencies | **Fixed.** `anyio==4.16.0` and `starlette==1.10.0` are pinned in `pyproject.toml` and match the lock file's `requires-dist`. `uvicorn` is pinned, and no other third-party import in `src` is undeclared. |
| Retirement of old request records | **Fixed.** Migration keeps only hashed, retired markers, and old request IDs correctly return `deleted_result`. The same hash weakness as above applies. |

## Minor issues (not blocking)

- **Migration can lock the database:** if any legacy record fails strict validation, migration aborts and the database won't open. The error reads like a tool-schema error and gives no way to export the raw data. Nothing is lost, because the migration rolls back.
- **Old exports are rejected:** JSON exports made before the fix that contain `server_delivery` now fail to import. The value is only rewritten during database migration. This matters little because v1 was never released.
- **`origin` can still be claimed:** `record_evidence` still accepts `origin: "imported"` from callers. The first review raised this under the provenance finding, and it is still open.
- **Windows encoding (unconfirmed):** `restrict_file` decodes `whoami` output with the locale codepage. A user or computer name with certain characters, like `É`, could raise a decode error and make `init-token` or `export` fail. Decoding as bytes with `errors="replace"` would avoid it, since the SID itself is ASCII.

This is an independent review by an AI model of code written by another AI model. It is not a human review or a formal security certification.
