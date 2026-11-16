# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

# Repertorio read-only review

I found no cross-profile access, auth bypass, origin, framing or raw-SQLite-leak defect that I could substantiate. I found three must-fix defects, in deletion leftovers, the demo command and session provenance, plus several smaller ones. Nothing was run; every finding comes from reading the code. The test files appeared partway through the review, so their owners are still writing them.

**Fully reviewed:** CONTRACT.md, `models.py`, `store.py`, `server.py`, `cli.py`, `selection.py`, `__main__.py`, `tests/test_store.py`, `tests/test_protocol.py`, `tests/test_cli.py`. I also checked the installed `mcp` 1.30.0 source for the APIs the server uses (`Server(version, instructions)`, `call_tool(validate_input=)`, `max_request_body_size`, `stdio_server(stdin=)`). They all match.

**Unreviewed or missing:** `evaluation.py`, `pilot.py`, `test_selection.py` and `test_evaluation.py` don't exist yet. I only skimmed `scripts/verify.py` (it runs ruff, mypy and pytest) and didn't review `uv.lock`, `evidence/*` or `docs/*`.

## Must-fix

**M1. Deleted record IDs stay in the database (`store.py` `prepare_delete`/`confirm_delete`, lines 457–459 and 485–486).**
- **Trigger:** `prepare_delete("all", [])` then `confirm_delete(token)`.
- **What happens:** `deletion_tokens.snapshot` holds `{kind: {id: sha256(body)}}`, so every deleted ID stays in plain text. Consumed, expired and never-confirmed tokens are never pruned. `requests` also keeps `request_id` and an unsalted `payload_hash` of the caller's payload. That payload has no server timestamps, so anyone who can read the database can confirm a guessed item ("was `book:x` with title Y saved?").
- **Why it matters:** IDs are user-chosen and stable, so they can be meaningful. This contradicts the `confirm_delete` tool description ("remove … recoverable derived records") and SECURITY.md.
- **Fix:**
  - Store one hash of the whole snapshot instead of the per-ID map.
  - On confirm, delete the profile's other tokens and keep only `token_hash, consumed`.
  - Prune expired tokens.
  - On retirement, blank `payload_hash` (`_replay` already checks `retired` before comparing hashes).
  - Add a test that no deleted ID survives in any table.

**M2. `repertorio demo` writes fake data into the real profile (`cli.py` `run_demo`, line 107; the `demo` command uses `--db`/`--profile` defaults).**
- **Trigger:** a new user runs `repertorio demo`. The default database and profile `default` are empty, so the demo proceeds.
- **What happens:** the demo permanently adds `everyday:shopping` (familiarity 0), a session and a `tutor_assessment` evidence record to the user's real profile. Afterwards, the user's own `prepare_context("opportunity_cost")` asks them a clarification question about that synthetic item, since it is the only reference rejected solely for familiarity. `academic_evidence_count` also counts the fake evidence, and a second `demo` run refuses to start.
- **Why the tests miss it:** `test_demo_real_mcp_persistence` uses a temporary database.
- **Fix:** default the demo to a temporary database, or require an explicit `--db` that isn't the default and a dedicated profile.

**M3. A "server_delivery" session record is just the caller's claim (`models.py` `Session`, lines 122–123).**
- **What happens:** `usage="delivered"` / `usage_origin="server_delivery"` are the defaults, and any caller can set them. `record_session({"id":"x"})` stores a session labelled as server-delivered, even though `prepare_context` keeps no record of what it delivered. A model can also attach any `context_reference_ids`, including ones that were never eligible.
- **Why it matters:** this contradicts the tool text "This tool cannot claim verified use", and the evaluation and pilot code will likely rely on this field. Evidence `origin="imported"` can be faked through `record_evidence` in the same way.
- **Fix:** rename the value to something like `client_asserted_delivery` and remove the default. If you want real attestation, have the server log delivery IDs and require sessions to cite one.

## Should-fix

1. **Windows executable lookup (`cli.py` `restrict_file`, lines 41–45).** `whoami` and `icacls` are called by bare name. Windows process creation searches the current directory before System32, so a planted `whoami.exe` runs during `init-token`, `export` or `demo --output` in an untrusted directory. Fix: use `%SystemRoot%\System32\…` absolute paths, or set the ACL through the Win32 API.
2. **Revision overflow breaks the profile (`store.py` `save_item` line 259; `models.py` line 54).** Import an item with `revision: 2147483647`, then save one edit. The stored revision becomes 2^31 without being re-validated. After that, every `save_item` on the item fails validation. Exporting the profile and importing it elsewhere fails entirely, because import is atomic. Fix: re-validate after incrementing, or reject the edit at the cap.
3. **Old v1 records aren't upgraded to the full record shape (`store.py` `_migrate`).** A v1 record with missing fields, like the one `test_v1_migration…` creates, conflicts when its own export is re-imported into the same profile: `existing.get("tags")` is `None` while the incoming record has `[]`. That breaks the contract's "re-import identical payload is a no-op". `save_item` also raises `KeyError` (reported as `internal_error`) if `created_at` is missing. Fix: normalise records through the model during migration. This is low priority because v1 was never released.
4. **Scopes aren't isolated from reading.** A credential with only `delete` can list every record ID through `prepare_delete("all")`. A credential with only `write` can test whether existing content matches a guess through import dry-run conflicts and `current_revision`. Either document this or require `read` as well.
5. **Unsupported claims:**
   - SECURITY.md:19 cites `docs/verification.md`, which doesn't exist.
   - `test_cli_rejects_large_import_before_database_change` is misnamed: `Store()` creates the database at `cli.py:246`, before `read_input` at line 268.
   - `evaluate` and `pilot` import modules that don't exist yet, so they fail with the generic "run doctor" message.
   - Oversized stdio input surfaces as an `ExceptionGroup`, so the intended message at `server.py:388` is replaced by the generic error (the exit code is still non-zero).
6. **Clean install:** `server.py` imports `anyio` and `starlette` directly, but `pyproject.toml` doesn't declare them; they only arrive through `mcp`.

## Known limits (not defects; the docs mostly state them)

- **Human consent isn't enforced by the server.** The deletion token is visible to the model, so with stdio `--allow-delete` the model can delete everything in two calls unless the host requires approval.
- **Physical erasure is best effort.** Deleted data can remain in the WAL file while another reader is active, in SQLite free pages, or in backups.
- **Windows doesn't restrict the database file.** Only token and export files get an ACL, so a `--db` outside a private folder inherits its parent's permissions.
- **Retries behave as designed but can surprise:**
  - Any deletion retires all of the profile's cached results, so a retry of an unrelated write returns `deleted_result`.
  - Replays return the original result, even if the record changed later.
  - An HTTP 408 can come back while the write still commits; retrying with the same `request_id` resolves it.
- **`get_profile` returns the user's raw text to the model.** Only `prepare_context` is limited to catalog text, so resistance to prompt injection depends on the host.

**Verified as correct:** every query is scoped to the configured profile, and HTTP identity comes only from the token. Writes are serialised, revisions are checked before updating, and imports commit all-or-nothing. Delete tokens are bound to the profile and to the full record contents, and they expire and work only once. Host and Origin are checked before authentication. Request size is capped through both content-length and chunked bodies, and error messages don't echo input.
