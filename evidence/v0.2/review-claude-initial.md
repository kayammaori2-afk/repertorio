## Verdict: GO, with small pre-merge fixes

I found no blocking code defects in the v0.2 surface. The seven earlier findings and the onboarding cutoff are fixed in the current code; I checked each one in the source rather than taking the closeout reports' word for it. Three medium issues sit in the pilot kit's honesty and integrity layer. They won't affect anyone until a human pilot runs, but each is a one- to ten-line fix. Before merging, the docs and release bookkeeping need updating (items 4–6).

The pilot does keep "materials prepared" separate from "approved" and from "participant data":
- `study init` reports `materials_prepared`, `human_rows: 0` and `recruitment_ready: false`.
- `study check` reports `ready_by_operator_declarations` and `human_reviews_verified_by_software: false`.
- `freeze` reports `independent_registration: false`.

## Defects

**1. Medium (not blocking): the usability "enrolled" denominator only counts people who have rows.**
- **Where:** `src/repertorio/study.py:303,319`. The guide claims the report "usa todos os inscritos como denominador" (`study-guide.pt-BR.md:27`), but line 47 of the same guide admits the program can't detect someone who was left out entirely.
- **Reproduction:** six people enroll and one drops out before any task. If the operator records no rows for that person, every task shows `"enrolled": 5`, and 5/5 unassisted `first_lesson` completions look like they meet the "5/6" progression rule.
- **Smallest fix:** rename the field to `participants_recorded` and add `"enrollment_reconciled_with_flow": false`. Then change the guide's line-27 claim. Reconciling against `flow.csv` would be stronger, but it needs a shared ID column.

**2. Low–Medium: the consent-review flag isn't tied to the text that was reviewed.**
- **Where:** `study.py:182-189,203-205`.
- **Reproduction:** render the consent, get it reviewed, set `consent_text_reviewed: true`. Then change `provider` or `withdrawal_and_limits` and render again. `check` passes and `freeze` succeeds, so the "reviewed" declaration now covers text nobody reviewed.
- **Smallest fix:** store the reviewed text's SHA-256 in a field like `consent_text_reviewed_sha256`. `check()` should compare it to the hash of the current `consent_text(protocol)`, or `render_consent` should reset the flag whenever the text changes.

**3. Low–Medium: the human learning-analysis path skips the kit's safeguards.**
- **Where:** the guide (`study-guide:37`) sends real data to `python -m repertorio.pilot --input`. The problems are in `pilot.py`:
  - It never checks readiness or the freeze, unlike `analyze_usability` (`study.py:263-280`).
  - It doesn't enforce opaque `p-` participant IDs.
  - It uses `write_text` and `mkdir(exist_ok=True)` (`pilot.py:250-276`), so it silently overwrites earlier output and writes without private permissions.
  - The report is titled "Pilot analysis demonstration" even for human data (`:260`).
  - It reads plain `utf-8`, not `utf-8-sig` (`:230`), so an Excel CSV with a byte-order mark crashes with a `KeyError`.
- **Smallest fix:** this can be fixed without touching the frozen analyzer. Add a `study analyze-learning` wrapper that runs `check` and verifies the freeze, then calls `analyze_csv`, and writes through `write_private` into a new directory.

**4. Low: stale or contradictory release docs.**
- `README.md:121` still says "131 local tests" (the v0.1 figure). For v0.2 it's 164 passed with 3 skipped on Windows.
- `docs/quickstart.pt-BR.md:43` suggests a prompt that never states the experience status. That recreates the observed first-use failure: following the guidance (`onboarding.py:94`), the assistant would correctly *not* record `completed`, so the learner gets the fallback instead of the analogy. Rephrase it as something like "Já faço compras semanais com orçamento…".

**5. Low (bookkeeping): update these after this review.**
- `CHANGELOG.md:3` still says "candidate, unreleased", and `evidence/v0.2/delivery-check.json` still says `candidate_not_released`.
- `docs/verification.md:9`, `verification.json` and `other-family-review.json` say no other-family review exists. Record this review as a static AI review only.
- `docs/v0.2.0.md:29` already describes a release page and receipt that don't exist yet. Make that true at publication or word it conditionally.

**6. Process: the working tree isn't committed.** `README.md`, `docs/quickstart.pt-BR.md` and `docs/v0.2.0.md` have uncommitted changes, and I reviewed the working tree. Commit them to PR #1 before merging.

**7. Low: the experiment analysis doesn't report what's missing.**
- **Where:** `experiment.py:416-431`. It reports `paired_cases` but not how many cases were planned, which cases were excluded from each contrast, or which arms the failures belong to. Failures appear only as opaque job IDs.
- **Fix:** add `planned_cases`, `excluded_case_ids` for each contrast, and failures grouped by arm, all from the operator key.

**8. Low: freezing doesn't check that no responses exist yet.** `freeze()` (`experiment.py:191-229`) accepts a `responses.json` that already has data. Requiring `responses.json == []` and no `blind-key.json` is a two-line guard. Beyond that, "a local manifest can't prove timing" is already a documented limitation.

**9. Low: file-size limits for frozen inputs don't line up.** `prepare` writes indented `jobs.json` and `cases.json` (`:176-178`), but `freeze` reads them with the 8 MB limit (`:62,223`). For example, 100 cases whose profiles carry many short evidence records copy the academic package into all 5 arms, and indentation can push the file past 8 MB. This is the same kind of problem as earlier finding 7. It fails safely before any data is collected; the fix is a size check in `prepare`.

**10. Low: setup recovery is rough.**
- If a file write or `icacls` call fails after `mkdir` (`setup.py:19,42`), the half-written directory blocks a rerun with a bare `FileExistsError`.
- `START-HERE.txt` could give the exact `doctor --db … --profile …` command.
- A lock file left by a crash (`cli.py:126-131`) needs manual removal, and no doc explains how.

## Status of earlier findings

| Finding | Status |
|---|---|
| 1. Editable blinding key | **Closed.** Analysis rebuilds the key from responses and checks the rater packets (`experiment.py:333-343`). |
| 2. Rubric generated after collection | **Closed.** The rubric is written at `prepare` (`:181`), included in the freeze (`:26`), copied as frozen (`:312`) and checked at analysis (`:339`). Rubric wording can still be edited before the freeze; only its structure is checked. That's still before collection. |
| 3. Empty consent passes | **Closed** for structure (`study.py:157-213`). See item 2 for the review-flag gap. |
| 4. Symlink destinations followed | **Closed** in the code (`cli.py:90-103`, `setup.py:17-19`). **Not run on Linux:** the 3 regression tests skip on Windows, and the repo has no v0.2 CI evidence. |
| 5. Concurrent credential updates | **Closed** for cooperating CLI writers (`cli.py:120-160`). |
| 6. Emoji paths break TOML | **Closed** (`setup.py:25-28`, test at `:97-107`). |
| 7. Response collection too large to read | **Closed** for responses. Item 9 is the same problem in the frozen inputs. |
| Onboarding cutoff / missing status | **Closed** (`onboarding.py:64-68,81,94`). The quickstart prompt (item 4) still contradicts it. |

## What checks out

- **Old clients:** the 9 original tools' schemas match the v0.1 Inspector capture (`concept` maxLength 160, `limit` ≤ 3). Topic aliases and `learning_options` are purely additive, and the database migrations top out at version 4.
- **Privacy:** `learning_options` never echoes learner titles. The setup snippets contain no secrets and grant no deletion. A search for personal paths or identity strings in the repo outside `.venv` found nothing.
- **Missingness:** blank, missing or failed values are never counted as zero, and the per-participant seven-day return value is checked for consistency.
- **Statistics:** the experiment's paired and equal-group averaging matches the documented complete-case method.

## What I could NOT verify

- **Nothing was executed:** no tests, lint, type checks, build or CLI runs. The pass counts and clean-install claims come from the repo's own evidence files.
- **Linux/macOS behavior,** including the 3 symlink regressions. Running the manual CI on the PR head before merging would cover the Linux part.
- **Python 3.11 and 3.12,** which `pyproject.toml` allows but CI doesn't test. I found no 3.12-only syntax by searching.
- **The wheel's actual contents.** The force-include of `pilot-protocol.md` looks correct on paper only.
- **Host behavior:** Claude, VS Code or Codex accepting the generated snippets, and any real host conversation.
- **The real state of PR #1** on GitHub, and whether the uncommitted edits end up in it.
- **The research content itself:** pedagogical correctness of the catalog and item bank, the consent wording's legal or ethical adequacy, and any real approvals, consent or participant data. None of that exists, and software can't establish it.

This is an independent AI static review, not an expert, security or ethics certification.