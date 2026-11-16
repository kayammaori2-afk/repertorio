# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

I found two remaining defects. One is in deletion: sessions that cite only catalog reference IDs survive deletion of the item they point to. The other is a broken link to a verification record that doesn't exist. The retired request-hash wording now accurately describes the bounded control. This was a static review with Read/Glob/Grep only. I ran nothing and edited nothing, and none of the commands below were executed.

## Scope
- **Read in full:** `evidence/review-initial.md`, `cli.py`, `store.py`, `server.py`, `models.py`, `docs/data.md`, `SECURITY.md`, `README.md`, `docs/quickstart.pt-BR.md`, `pyproject.toml`.
- **Read in part:** the deletion, migration and Windows tests in `tests/test_store.py` and `tests/test_cli.py`, `selection.py:60-92`, the output handling in `evaluation.py` and `pilot.py`, the `repertorio-mcp` entry in `uv.lock`, and the reference and item IDs in `catalog.json`.
- **Not reviewed:** the logic of evaluation and pilot, `test_protocol.py`, `test_selection.py`, the evidence logs, and the rest of `docs/*`.

## Retired request hashes: accepted as a documented limit
The claims now match the code.
- **Deleted data doesn't come back through the product.** `confirm_delete` blanks `operation`, `payload_hash` and `result` and keeps only `sha256([profile, request_id])` with `retired=1` (`store.py:670-673`). Every preview for the profile has its `kind`, `ids` and `snapshot` erased (`store.py:676-679`). Replay checks `retired` before comparing anything (`store.py:270`). Export returns only active records.
- **Plaintext request IDs are never stored.** The current schema writes only the hash (`store.py:259`), and migration from v2 hashes the old plaintext IDs (`store.py:226-230`).
- **The residual is disclosed in the right places:** the `Store` docstring (`store.py:98-106`), `docs/data.md:32` and `SECURITY.md:9`.
- **The guidance reaches callers.** `REQUEST_ID_GUIDANCE` is in the `request_id` schema field and in the description of every write tool. The CLI's `--request-id` help repeats it, and the CLI and demo generate UUID4 values by default.
- **Tests cover the limit.** `test_store.py:439-492` uses a deliberately meaningful ID. It shows the plaintext and the payload digest are gone from `iterdump`, the guessed key still confirms, and a different payload guess gets the same `deleted_result`. It also shows another profile with the same raw ID is unaffected.
- **What remains is forensic, not a product leak.** The product can't recover content from these markers. A database reader who guesses an ID can confirm the request existed, which the spec doesn't forbid and the docs state.
- **Optional wording fix:** the `confirm_delete` tool text (`server.py:202`) says nothing about the markers, so a model may tell the learner "everything is gone." Adding "Opaque retired request markers remain to block stale retries" would fix that.

## Unresolved material defects

**D1. Deletion keeps sessions that link to the deleted item only through catalog references (`store.py:571-591`).**
- **Trigger:** a host records a session such as `record_session({"id":"s","usage":"reported","usage_origin":"self_report","context_reference_ids":["oc-shopping"]})` with no `repertoire_ids`. The schema allows this, and the tool text ("use with context IDs") encourages it. Then the user deletes the repertoire item `everyday:shopping`.
- **What happens:** the dependency closure only follows `repertoire_ids` and `evidence_ids`. The session survives, but `oc-shopping` maps to `item_id: "everyday:shopping"` in `catalog.json:27-29`, so the export still shows the learner had that item.
- **Usage history comes back:** if the item is added again, `selection.py:80-85` restores the `documented_prior_use` score from the surviving session.
- **The code's own claims are wrong:** the comment at `store.py:571-572` ("No remaining product record may retain a link…") and the preview's "dependent sessions … are removed" text both say otherwise.
- **Minimal repair:**
  1. In `_selection`, build `{ref["id"]: ref["item_id"]}` from `catalog()["references"]`.
  2. Also select a session if any of its `context_reference_ids` maps to an `item_id` in `selected["repertoire"]`. The snapshot hash then covers it automatically.
  3. Add a test where a session that has only `context_reference_ids=["oc-shopping"]` appears under `affected.sessions` and is removed.
  4. Keep in mind that IDs from an older catalog version won't resolve. Either document that, or require `repertoire_ids` to include the implied item IDs when the session is recorded.

**D2. `docs/verification.md` doesn't exist, but four documents cite it.**
- **Where:** `README.md:65` and `:69`, `SECURITY.md:19`, `CHANGELOG.md:5`, `docs/contribution.md:5`. `scripts/verify.py:35` writes only `evidence/verification.json`.
- **Status:** the earlier review flagged this, and it is still open.
- **Why it matters:** this is the document cited as the record of "executed defensive tests and review".
- **Repair:** either point the links at `evidence/verification.json` and the logs, or write the document with a factual summary.

## cli.py, store migration and declared origin
**These items look correct:**
- **System tool lookup:** `whoami.exe` and `icacls.exe` are called by absolute path under `SystemRoot\System32`. A relative or drive-relative `SystemRoot` is rejected before anything runs, and `write_private` then removes its temporary file.
- **Decoding:** output is read as bytes and decoded as UTF-8 with replacement, which is fine because only the ASCII SID field is used. The tests cover both the valid and the rejected cases.
- **Migration:** it runs in one transaction and normalises records through the models. The `migration_invalid_record` error is actionable, doesn't echo the bad value, and the test shows a v2 database is left unchanged after a failure. `server_delivery` is rewritten to `client_reported_delivery`.
- **Declared origin:** `Evidence.origin` is described as caller-declared (`models.py:102`, `store.py:439`, `docs/data.md:32`), and selection never reads `origin`.

**Minor issues:**
- **Demo `--db` detection (`cli.py:351`):** detection scans the raw arguments, but argparse accepts abbreviations. `repertorio --d x.sqlite3 demo` therefore runs against a temporary database and reports it as temporary. That is safe, but not what was asked. Fix: `ArgumentParser(allow_abbrev=False)`, or give `--db` a default of `None` and resolve it later.
- **Demo output path:** the existing-output check happens after the demo runs (`cli.py:362`). If the output file already exists, the demo has already filled the profile, and the command then fails with `File exists`. Fix: check `args.output` before calling `run_demo`.
- **Inconsistent migration errors:** the other migration errors (`store.py:191-201`) use the default code `invalid_input` and don't include the backup advice. Give them the same code and message.
- **SID check:** the SID isn't validated. Unexpected `whoami` output raises an `IndexError` and the user sees the generic "run doctor" message. Optional fix: check it against `^S-1-[0-9-]+$`.

## README and quickstart: static check against the parser and dependencies
- **These match the parser:** global options before the subcommand (`--db`, `--profile`), `demo --output`, `init-token --credentials-file/--token-file/--scopes read write`, `serve --transport http --credentials-file --host --port`, `export --output [--format summary]`, `import --input [--apply]`, `evaluate`/`pilot --output DIR` (both create or overwrite the directory), and the CSV import in `docs/data.md:19`. `examples/repertoire.csv` exists.
- **Dependencies:** `anyio` and `starlette` are now pinned in `pyproject.toml:11`, and `uv.lock:1287-1312` matches. `uv sync` installs the `dev` group by default, which `scripts/verify.py` needs. I can't confirm statically that the lock is current.
- **Linked files:** all exist except `docs/verification.md` (D2).
- **Rerunning the demo:** both guides say to use a new `--profile` and a new `--output` for another run. That is correct, given the empty-profile check and the refusal to overwrite the output file.

## Accepted, documented limits (not defects)
- Retired request-key hashes and profile names remain in the database (`docs/data.md:32`).
- Physical erasure is best effort. Deleted bytes can remain in the WAL, free pages, backups, host transcripts and exports.
- The deletion token is visible to the model, so human consent depends on the host's approval flow.
- On Windows the database file itself gets no ACL.
- Session and evidence provenance is client-reported, not attested.

This is a code-reading review. It is not a certification, and it doesn't stand in for a human security review.
