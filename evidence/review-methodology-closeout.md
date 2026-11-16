# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

All four findings are fixed, and I found no remaining material defects in the repairs. This was a static read only: I ran nothing, changed nothing, and didn't check that the manifest hashes match the current file bytes. It is not a human or expert certification. Everything here stays synthetic, shared-author and descriptive.

## Closure status

**1. "dezes7" typo — closed**
- The prompt now reads "realizar 17 custa 117" in `data/pilot_items.json:30`, `docs/pilot.md:28` and the copied `evidence/pilot/pilot_items.json:30`. "dezes7" now appears only in the change notes in `frozen_manifest.json:7` and `freeze_history_v2_1.json:7`.
- The answer key is unchanged and correct: 117 − 106 = 11, and 19 − 11 = 8.
- The mixed-token check at `tests/test_evaluation.py:138` would have caught "s7".
- The answer-key test (`tests/test_evaluation.py:157-170`) is a real regression test. With the old text it would have extracted 127, 16, 106, 117, 19, so the check at line 162 (`quantities[3] == quantities[1]+1`) would fail. It also checks that the probability numerator and denominator come from the prompt.
- The bank is re-frozen as `pilot-bank-v3-post-followup` under `freeze-v3-post-followup`.

**2. Tie randomization and how REPORT.md presents it — closed**
- C now randomizes ties among its own scores (`evaluation.py:205,225-226`). It uses the same `score_reference` totals that `prepare_context` uses, with a random draw replacing the ID tie-break, so it matches the production order apart from ties.
- B's randomization matches the fixed pipeline. The reference-ID tie-break that remains in B can't matter, because the catalog has exactly one reference per item and concept.
- Per-case values in `diagnostics.json` behave as expected. Cases with no ties give a single value (for example, marginal_analysis-general and conditional_probability-general). Cases with ties show a range (for example, independence-excluded at 0.63–1.0).
- REPORT.md lines 20–25 give B, C and D means by split and report the sign change on held-out cases: −0.0503 with ID-order ties versus +0.1514 with random ties. The sign is computed from the results (`evaluation.py:499-506`), and the report says neither tie rule addresses label circularity. `verification.md:35` says the same.
- The ID-order result is still primary, and the report's opening sentence now names the tie rule it depends on.

**3. Fit/grade Spearman cuts — closed**
- REPORT.md lines 27–36 give 5/24 exact matches.
- They also split ρ by scenario (baseline-strength −0.41 vs. other 0.55) and by concept, each next to that group's fixed-order C−B. Opportunity cost has ρ 0.83 with C−B +0.29; conditional probability has ρ −0.17 with C−B −0.17.
- Per-cut exact-match counts are computed (`evaluation.py:265`) and stored in `summary.json`, but the REPORT table doesn't show them. My original fix only asked for the overall 5/24, so this isn't a defect.

**4. Probability criterion 4 — closed**
- The criterion (`pilot_items.json:126`, `docs/pilot.md:48`) now asks for what the prompt asks: that the condition restricts the draws to the named group. It says that saying only that group is considered is enough.
- There are two scoring examples, in `pilot_items.json:140-143` and `docs/pilot.md:56`:
  - "because we only consider the 28 volcanic rocks" earns the point.
  - "because 28 is written in the question" doesn't.
- The carry-forward rules and the P_CONDITION_EXPLANATION error code still agree with the criterion. The prompt wording is unchanged.

**Smaller issues from the last review that are also fixed**
- `docs/evaluation.md:21` no longer says "independently eligible".
- The pilot REPORT bounds are now labelled "C−B, 0–8 score scale".

## Optional cleanups (not material)
- REPORT.md line 7 still says random-tie diagnostics "are in diagnostics.json", though the report now summarizes them. That's true but slightly out of date.
- The `earns_point` note in the JSON says "explicitly links", while the criterion allows the link to be implicit. Using "links", as `docs/pilot.md:56` does, would be cleaner.
- The answer-key test reads numbers by position and doesn't check how many there are or that `excluded_total` equals the first number. It still fails loudly if the text drifts.
- The `docs/pilot.md` heading says "protocol v2", while the bank is v3.

What's left for you is running the final tests and the clean-wheel reproduction to confirm the manifest hashes match the current bytes.
