# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

I'm closing D1. Under the documented trusted-client/historical-link boundary, I found no remaining material flaw in these changes. This was a static read only; I didn't run the tests.

## What resolves D1

- **Links are saved when a session is written.** `Store._bind_session` (`store.py:383-408`) runs on `record_session` (`store.py:482-483`) and on import (`store.py:536-537`). If a session uses the current or `unknown` catalog version, each known context reference is turned into its item ID and saved in `repertoire_ids`. An `unknown` version is stamped with the current one once every reference resolves.
- **Unknown cases need declared links.** An unknown reference, or an explicitly different catalog version, needs a nonempty `repertoire_ids`. `_check_links` (`store.py:377-378`) then checks those IDs exist in the same profile, inside the same transaction. Whether the list is complete is the caller's word, not checked, and `docs/data.md:9` says exactly that.
- **Deletion also checks the current catalog.** `_selection` (`store.py:630, 645-658`) builds the reference-to-item map from the live catalog. It selects any session whose `context_reference_ids` map to a selected item. That set goes into the snapshot hash, so the preview and the confirmation agree.
- **Prior use can't come back.** `score_reference` (`selection.py:80-85`) decides prior use by matching reference IDs against the current catalog. Deletion uses that same current-catalog map, so after a delete no surviving session can match a reference that points to the deleted item. Re-adding the item can't bring the prior-use score back. The test checks this at `test_store.py:734-736`.
- **Migration from schema 3 to 4** (`store.py:238-271`):
  - It backfills the links.
  - For each changed profile it re-checks links and size, then retires that profile's receipts and previews.
  - All errors from `_bind_session`, validation and `_check_links` are subclasses of `ValueError`, and they become `_migration_error()`. Because they fire inside the `_migrate` transaction, everything rolls back.
- **The tests match the claims** (`test_store.py:697-851`):
  - a context-only session plus its evidence is deleted;
  - replays are scrubbed and return `deleted_result`;
  - re-adding the item gives no prior use;
  - a repeated import is a no-op;
  - the catalog is removed and a portable export restored;
  - an unknown reference or version is rejected atomically, then accepted with declared links;
  - the current-catalog fallback works on legacy records;
  - migration backfills links and retires old receipts;
  - an unresolvable migration rolls back and keeps the original body.
- **The docs agree.** `docs/data.md:7-9` matches the code. D2 is also fixed: `docs/verification.md` exists, and the README and SECURITY links now point to it.

## Minor issues (none blocks closure)

1. **The most likely leftover from the old bug isn't tested.** That is a schema-3 session with only `oc-shopping` whose `everyday:shopping` item was already deleted under the old logic. The reference resolves, so `_check_links` fails and the migration rolls back. That fails closed and matches the documentation. But:
   - only an unresolvable reference is tested (`test_store.py:839`);
   - migration runs over every profile, so one bad record blocks the whole database file for all profiles;
   - the only advice is generic ("inspect the legacy records... locally"), with no fix possible inside the product.

   Worth a test, and perhaps a sentence telling users to remove or relink that session first.
2. **Deletion can remove more than it should.** For a session recorded under another catalog version, the current-catalog check can select it even if, in its own version, the reference pointed to a different item. That only deletes more, never less, and the preview lists it. `docs/data.md:32` ("Related sessions/evidence may be removed…") roughly covers this.
3. **The `docs/verification.md` wording is a bit broad.** "Complete deletion of sessions linked through catalog context references" (`docs/verification.md:29`) is wider than the limit stated in `docs/data.md:9`. Suggested wording: "…for current references and declared historical links."
4. **The tool text doesn't mention the link rule.** The `record_session` description (`server.py:168`) doesn't say that unknown references or versions need `repertoire_ids`. The error message is clear about it, so this is optional.
