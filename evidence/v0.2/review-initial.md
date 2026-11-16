The main blocker is the experiment’s integrity chain: analysis can accept changed condition assignments and provenance without detecting them. I found seven concrete defects below. Reproduction paths are derived statically; I used no tools and ran no tests.

1. **High — Analysis trusts an editable blinding key.**  
   `src/repertorio/experiment.py:313–318,323,358–362,392–402`

   `check_freeze()` protects the original operator key, but analysis trusts `blind-key.json` for response-to-job assignments, failed jobs, and `dataset_kind`. That file is neither independently validated nor included in the reported input hashes.

   **Reproduction:** Give one case’s C response scores of 3 and its E response scores of 0. After blinding, swap those two job-ID values in `blind-key.json`. Leave responses, ratings, and frozen files unchanged. Analysis passes and reverses C−E from +3 to −3. Similarly, changing only the key’s `dataset_kind` changes the reported provenance despite unchanged response declarations.

   **Fix:** Reconstruct and validate the mapping, failures, and dataset kind from the response records and frozen jobs. Include the validated blinding artifacts in analysis provenance. The stored `packet_hash` at line 269 is also never checked; analysis should verify the actual scoring packet supplied to raters.

   This is a missing consistency check, separate from the documented inability to authenticate people or prevent deliberate replacement of an entire local archive.

2. **Medium — The rubric is generated after collection and excluded from the prospective freeze.**  
   `src/repertorio/experiment.py:159–164,194–198,280–288`; `docs/tutor-evaluation.md:22`

   Preparation produces no rubric. Freezing hashes only plan, cases, jobs, and operator key. `blind()` subsequently generates the rubric from whichever code version is installed then.

   **Reproduction:** Freeze an experiment, collect responses, then change the rubric literal or install a version with different scoring instructions. Blinding uses the new rubric while `check_freeze()` still succeeds. Editing the generated rubric is likewise undetected.

   **Fix:** Materialize the rubric and scoring specification during preparation, include them in the prospective manifest, and copy those exact frozen materials into the rater packet. Archiving the package checksum manually helps, but does not make the current command freeze the rubric as instructed.

3. **Medium — An empty consent document passes the completeness check.**  
   `src/repertorio/study.py:144–169,173–190`

   Consent validation checks only for `[` and `RASCUNHO`. Empty or whitespace-only text contains neither.

   **Reproduction:** Complete the required declarations and settings, set the three Boolean declarations to `true`, and truncate `participant/consent-DRAFT.txt`. `check()` reports ready, and `freeze()` accepts the empty document.

   **Fix:** Reject empty consent text and check required content fields before rendering the participant document. Continue describing human review as declared rather than authenticated. This finding concerns basic completeness, not software verification of ethical approval.

4. **Medium — Resolving paths before exclusive creation follows dangling symlinks.**  
   `src/repertorio/cli.py:86–92`; `src/repertorio/setup.py:16–18`

   `O_EXCL` protects the resolved destination, but `Path.resolve()` has already followed an existing final symlink.

   **Reproduction:** Make the requested export filename a symlink to an absent file elsewhere. `write_private(..., replace=False)` creates the referent instead of rejecting the occupied requested pathname. Similarly, point the setup output directory symlink at an absent directory: setup resolves it and creates its artifacts there.

   **Fix:** Preserve and check the final pathname, rejecting existing symlinks/reparse points before creation; use exclusive creation without following that component. Where protection against concurrent directory manipulation is required, use platform-appropriate directory-relative operations.

   Ordinary existing regular files remain protected. This is a destination-boundary defect, not evidence that default writes overwrite existing regular-file contents.

5. **Medium — Concurrent credential updates lose changes and can restore revoked credentials.**  
   `src/repertorio/cli.py:117–136`

   Registry updates use an unlocked read–modify–replace sequence. Atomic replacement prevents a torn file, but not a stale update.

   **Reproduction:** Two `init-token` processes read the same existing registry, append different credentials, and replace it successively. Both can report success, but the later replacement removes the earlier addition. A revocation performed between another process’s read and replacement can similarly be undone.

   **Fix:** Serialize registry mutations with an interprocess lock or transactional storage. Revocation must use the same coordinated mutation mechanism. Add a concurrent-update regression case.

6. **Medium — Generated Codex TOML fails for valid non-BMP Unicode paths.**  
   `src/repertorio/setup.py:24–27`; `tests/test_onboarding.py:52–65`

   JSON string encoding is not universally valid TOML string encoding. With `ensure_ascii=True`, an emoji becomes two surrogate escapes, such as `\ud83d\udcda`; TOML Unicode escapes must represent Unicode scalar values.

   **Reproduction:** Generate setup files with a database path containing `📚`. The JSON snippets remain valid, but parsing `codex.config.toml` with `tomllib` fails. The supplied test covers spaces and `ç`, which do not expose this difference.

   **Fix:** Use a TOML serializer or a correctly implemented TOML string encoder. Test non-BMP characters in both interpreter and database paths.

7. **Medium — Permitted experiment sizes can produce an unreadable response collection.**  
   `src/repertorio/experiment.py:45–48,74–75,125,221,243–248`

   The workflow permits 100 cases × five arms and up to 20,000 characters per completed response, but rejects every JSON input larger than 8,000,000 bytes.

   **Reproduction:** Prepare 100 cases and collect 500 otherwise valid records with 20,000 ASCII characters each. Text alone exceeds 10 MB. `blind()` rejects the file before validating its records, although the collection fits the stated individual limits.

   **Fix:** Make aggregate budgets consistent during preparation/freezing, or use bounded per-response files or streaming ingestion. Reject incompatible plans before collection rather than requiring a frozen study to be split afterward.

There is also a **conditional onboarding defect** at `src/repertorio/onboarding.py:63–77`: `candidate_pool()` examines only the first 100 references per concept (`selection.py:64–66`), while onboarding iterates every reference and treats an absent rejection entry as eligible. With 101 references and an empty profile, reference 101 appears `ready=True`; an excluded item beyond the cutoff can also be suggested. Fix this in onboarding by using only evaluated candidates or explicitly checking every displayed reference. The omitted catalog prevents determining whether this is reachable in the supplied release.

The following are **documented limitations, rather than undisclosed defects**:

- **Usability denominator:** `study.py:250–266` counts distinct participants present in task rows. Removing all five rows for someone reduces the reported “enrolled” count without detection. The guide explicitly requires manual reconciliation with `flow.csv` at line 47. That limitation is disclosed, but the output does not independently establish an all-enrolled denominator. Reading a reconciled enrollment roster would strengthen it.
- **Tutor statistics:** The displayed paired differences and equal-group means are arithmetically consistent with the documented complete-case method. Missing pairs can change the included groups and comparisons; failure reporting does not remove that selection limitation.
- **Interpretation:** Reused synthetic cases, declared identities/settings, partial masking, ordinal ratings, single generations, public assessment items, and absent human learning outcomes are explicitly acknowledged. I would not relabel these as independent validation or efficacy evidence.
- **Empty kit:** The shown initialization writes header-only observation files. It does not manufacture human outcomes.

I cannot verify storage isolation, correction merging, revision conflicts, idempotency, or deletion semantics because `store.py` is absent. The omitted `evaluation.py`, `pilot.py`, catalog, item bank, and canonical pilot protocol also prevent checking arm construction, whether `academic_package` carries the promised objective/evidence, assessment correctness, or the frozen learning analyzer.

Packaging declarations appear to account for the copied pilot protocol, but source inspection cannot establish wheel contents, dependency availability/compatibility, or actual assistant-host installation. The SDK subprocess test is useful integration coverage; it does not establish usability in Claude, VS Code, or Codex, particularly from a clean installed environment outside the checkout.

This is an AI static review, not expert certification, a security certification, or evidence of tutor quality or human learning.