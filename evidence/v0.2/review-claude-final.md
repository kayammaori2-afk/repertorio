## Verdict: GO. A, B, C and all four nits are closed, and none of the corrections introduces a regression.

| Item | Status | What I checked |
|---|---|---|
| **A** Freezing after data is collected | **Closed** | `study.py:251-253` compares the bytes of `usability.csv` and `learning.csv` against `csv_template(...)` before it builds the manifest. The comparison is sound: `write_private` writes with `newline="\n"` (`cli.py:106`), so the template's CRLF bytes reach disk unchanged. In `test_release_review.py:79-86`, the freeze is first refused after the fixture rows are written. Only the artificial fixture is then reset to the template; the test freezes and writes rows afterwards. `:156-164` covers usability and asserts that no manifest is created. The other `study.freeze` calls in the tests are either expected to fail on pending declarations or run on empty tables (`test_research_workflow.py:286`, where the rows are written at `:289-292`, after the freeze). The guide (`study-guide.pt-BR.md:11`) now says the tables must be exactly as generated, and that this check can't prove the order of events if an operator removes and restores data. |
| **B** Learning protocol in the kit | **Closed** | `docs/pilot.md:75` now says the commands are for reproducing synthetic output, directs human data to `study analyze-learning` after freezing, and says the legacy command doesn't enforce the kit's safeguards. `pyproject.toml:31` still maps it to `data/pilot-protocol.md`. This now agrees with `study-guide:37`. `pilot.py` and the frozen inputs are unchanged. |
| **C** Setup recovery message | **Closed** | `setup.py:62-65` includes `({exc})` and keeps `from exc`. `setup.py:15` imports `write_private` inside the function, so the monkeypatch in `test_release_review.py:135-153` takes effect. That test runs through `main`, checks that stderr contains both `icacls` and `new --output`, and that the earlier file and the missing database are as expected. |
| Nit: consent restore | Closed | `test_research_workflow.py:297` restores the consent with `write_bytes(...encode("utf-8"))`, so the form-X tamper check at `:298-301` now tests form-X on Windows too. |
| Nit: single read | Closed | `study.py:300-304,340`: a bounded read of 1 MiB + 1 byte, decoding from `raw`, and the hash is taken over that same `raw`. |
| Nit: unfrozen error | Closed | `study.py:272-277` turns `FileNotFoundError` into a `ValueError` that tells the operator to freeze, and the test matches on "not frozen". |
| Nit: command list | Closed | `v0.2.0.md:18` now lists `init/consent/check/freeze/analyze-usability/analyze-learning`. |

## Remaining release blocker

There's no code blocker. One bookkeeping item has to be fixed before tagging, as you planned:
- **`docs/v0.2.0.md:29`** says the release page and its external receipt already exist.
- **`docs/v0.2.0.md:25`** still mentions only the same-family review.

Either update both to match what actually happens or soften them. Also commit the tree, since `test_release_review.py` and the evidence files are still untracked.

One non-blocking point, which I'm not asking you to change: the first-freeze check covers only the usability and learning tables, not `scoring.csv` or `flow.csv`. Like the other checks, it's a local guard that only holds if the operator is honest.

## What was not executed

I only read files; I ran nothing:
- No tests, lint, type checks, builds, wheel inspection or CLI runs.
- Your test counts, CI results and the final release receipt are your claims, not things I confirmed.
- I didn't check whether `candidate-ci.json` reflects these uncommitted corrections. It predates them.
- I didn't check the state of PR #1, Python 3.11 or 3.12, or whether hosts accept the snippets.

Software checks also can't establish consent adequacy, ethics approval, pedagogical validity, reviewer independence, or whether any human data is real. The repository holds only artificial fixtures and empty templates. This is an independent static review by an AI from a different model family, not human validation of the security, ethics or education aspects.
