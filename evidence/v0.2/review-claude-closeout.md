## Verdict: GO for merge and release of v0.2.0 as honestly labeled empty study software

I re-read the changed code, tests and prose myself; I didn't rely on the disposition list. Every initial code finding is closed or narrowed to a documented limit, and the changes introduce no blocking defect. I found three new low-severity problems (A–C below) and some nits. I'd fix A before merging because it takes about five lines, but none of them blocks release. The frozen v0.1 analyzer (`pilot.py`), the selector and the benchmark inputs are unchanged; `analyze_learning` calls `pilot.analyze` without modifying it.

Throughout this report, "guard" means a local check that works only if the operator is honest. None of these checks proves who approved anything, when consent was reviewed, the order in which things happened, or that a person exists. The repository contains only artificial fixtures and empty templates.

## Status of the initial findings

| # | Status | What I checked |
|---|---|---|
| 1. Enrolled denominator | **Closed** | `study.py:404,416` reports `participants_recorded` and `enrollment_reconciled_with_flow: false`. The learning report says "Participants recorded…" (`:342`). The guide no longer claims all enrollees are counted, and gives the 5/5 ≠ 5/6 warning (`study-guide.pt-BR.md:27`). Test at `test_research_workflow.py:233-235`. |
| 2. Consent review not bound to the text | **Closed** | The SHA-256 is compared against the current rendered text (`study.py:226-230`). The declaration is cleared *before* changed text is written (`:192-196`), and rendering is refused after freeze (`:187`). This binds the declaration to the bytes; it does not authenticate the reviewer. |
| 3. Learning analysis skips safeguards | **Closed for the kit path** | The new wrapper does all of these: readiness and freeze check for declared-human data (`:306`, `:266-284`), BOM support (`:294`), exact columns (`:296`), short or long rows rejected (`:308`), `p-` IDs (`:312`), finite non-negative numbers (`:322-324`), validation before any output exists, a new directory created with `exist_ok=False`, private files, input and freeze hashes (`:330-331`), and a title that matches the data (`:336-338`). The legacy unguarded command still exists, as documented; see B. |
| 4. Stale docs | **Closed** | `README.md:121` no longer gives a test count. `quickstart.pt-BR.md:43` now says the learner already does weekly shopping ("Já faço… que já pratiquei"), which maps to `completed`. |
| 5. Bookkeeping | **Pending, as you said** | `v0.2.0.md:29` still says the release page and receipt exist, and `:25` mentions only the same-family review. Not a code defect. |
| 6. Uncommitted tree | **Still open** | The git snapshot shows modified files, plus `test_release_review.py` and `candidate-ci.json` untracked. Commit them before merging. |
| 7. Experiment missingness | **Closed** | `experiment.py:407,430-432` adds planned cases and excluded case IDs per contrast; `:451-458` groups failures by arm using the operator key. Tested at `test_research_workflow.py:122-130`. |
| 8. Freeze after collection | **Closed for the experiment** | `experiment.py:212-218` refuses a non-empty `responses.json` or an existing `blind-key.json`. Exclusive-create `write_json` also stops a re-freeze. A dishonest operator could still empty the file, freeze and restore it, as `tutor-evaluation.md:66` states. |
| 9. Frozen-input sizes | **Closed** | `experiment.py:185-194` measures the exact indented UTF-8 serialization before `mkdir`. `write_private` writes with `newline="\n"` (`cli.py:106`), so the size on disk matches the measured size on Windows too. |
| 10. Setup recovery, doctor command, stale lock | **Mostly closed** | The exact PowerShell or shell doctor command is in START-HERE (`setup.py:29-34,53-55`), with correct quoting. The stale-lock procedure is clear (`SECURITY.md:3`). The recovery message has a gap; see C. |

## New findings

**A. Low–Medium: `study freeze` accepts data that was already collected, so the new human-data guard can be satisfied after the fact.**
- **Where:** `study.py:245-263`. Freeze checks the declarations but never checks that `usability.csv` or `learning.csv` still match their templates. The experiment refuses this case; the study kit, which is the one meant for people, does not.
- **Reproduction:** the repo's own test does it. `test_release_review.py:74` writes declared-human rows, and only then calls `declared_ready` and `freeze` (`:77-80`). The freeze succeeds, and `analyze-learning` then produces an "Exploratory human pilot analysis" with a `study_freeze_sha256`. The guide's "freeze before collecting" (`study-guide:11`) is never enforced.
- **Smallest fix:** add this to `freeze()` before building the manifest:
  ```python
  for name, fields in (("usability.csv", USABILITY_FIELDS), ("learning.csv", list(synthetic_rows()[0]))):
      if (directory / name).read_bytes() != csv_template(fields).encode("utf-8"):
          raise ValueError("Freeze before recording observations; start a new study version.")
  ```
  Compare bytes: `csv_template` writes `\r\n` line endings, which `read_text` would normalize away. Then move the fixture write in the test to after `study.freeze`. This is still only a guard: an operator could empty the files, freeze, and put the rows back.

**B. Low: the learning protocol copied into the kit still sends real data to the unguarded command.**
- **Where:** `docs/pilot.md:75` says the CSV "can be replaced by consented, reviewed study data" for `python -m repertorio.pilot --input` (`:72`). `study.py:94-100` copies that text to `operator/learning-protocol.md`, which the guide tells operators to follow (`study-guide:35`).
- **The contradiction:** the guide (`:37`) says to use `study analyze-learning` instead, so the kit's two documents disagree.
- **Smallest fix:** replace that sentence with: "For human data use `repertorio study analyze-learning`; this command reproduces synthetic output only." This changes protocol prose and the kit file's hash, not the analyzer or any frozen numerical inputs.

**C. Low: the setup failure message tells the user to resolve a "reported" problem that is never reported.**
- **Where:** `setup.py:62-65` wraps the original error. `cli.py:624` prints only `str(exc)`, which drops `__cause__`, so the real cause (the `icacls` failure, the SID lookup, the path) never appears.
- **Reproduction:** run the monkeypatch from `test_release_review.py:129-144` through `main([... "setup", "--output", ...])`. Stderr shows only the generic sentence.
- **Smallest fix:** `raise OSError(f"Setup could not finish ({exc}). Preserve the partial directory …") from exc`.

**Nits (not material):**
- `test_research_workflow.py:297` restores the consent with `write_text`, which writes CRLF on Windows. On Windows, the form-X tamper check at `:298-301` therefore passes because of the consent bytes, not form-X. Ubuntu still tests it properly. Fix: `write_bytes(...encode())`.
- `study.py:330` hashes a second read of the file rather than the bytes that were parsed. Read once.
- An unfrozen human analysis fails with a raw `FileNotFoundError` errno message (`study.py:269`). It fails safely, but the message is unclear.
- `v0.2.0.md:18` lists `study init/check/freeze/analyze-usability` and omits `consent` and `analyze-learning`.

## What I could not verify

- **Nothing was executed.** No tests, lint, types, build or CLI runs. The 42 passed and 1 skipped, the local Python 3.11 run of 164 passed and 3 skipped, and the final gates are your execution claims, not mine.
- **`candidate-ci.json` doesn't contain the test counts.** It shows both jobs (`ubuntu-latest` and `windows-latest`, Python 3.13 only) succeeding on `10f114f`, including the "Show exact test results" step. It has no test counts or skip list, so I can't confirm "167 on both" or that the symlink tests ran on Linux. It also predates these uncommitted corrections.
- **Unverified:**
  - the wheel's contents
  - Python 3.11 and 3.12
  - host acceptance of the snippets
  - the actual state of PR #1
  - the publication receipt
- **Research content:** whether the consent is legally or ethically adequate, the pedagogical quality of the item bank, real approvals, and real reviewers. None of these exists yet, and software checks can't establish them.

This is an independent static AI review from a different model family. It is not a human security, ethics or education certification.