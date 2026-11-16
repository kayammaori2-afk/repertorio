# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

I found 10 material problems. Three of them weaken the headline result: catalog prompts overlap the pilot test items, the relevance labels copy the selector's main score input, and baseline B's ranking comes down to alphabetical order. On the designated held-out split, C does slightly worse than B.

Findings 1–6 are about the internal synthetic evaluation, where the same author wrote the catalog, cases and labels. Findings 7–10 are protocol and analysis problems to fix before any real recruitment. Nothing here requires real participants now.

## Findings

**1. High: pilot test items leak into the context the arms receive** (`catalog.json` `transfer` fields vs. `docs/pilot.md` items; delivered through `render_reference` in `selection.py`)
- `cp-cards` says "Of 24 students who chose art, 9 also chose music." Form X probability uses the same 24 and 9 (theater/music).
- `cp-bags` (30 evening members, 12 cycle) matches Form Y's 12/30. Its shift-and-cycling theme also matches the baseline item.
- `ma-cooking` (printer, fixed setup fee, extra cost 3, offer 5) matches Form X economics (cost 3, offer 5, fixed 90) and the baseline's printer setup.
- The exposure differs by arm: A gets none of these, B gets `cp-cards` in cp-general, C gets `cp-bags`, and both B and C get `ma-cooking`. This breaks pilot.md's rules "no test item in instruction" and "quantities differ from every test item".
- The scripted lesson examples (a cooking portion and a bag subset) are also C's top references, which blurs the A/C contrast.
- **Repair:**
  - Rewrite either the item bank or the catalog's transfer/diagnostic text with different numbers and contexts.
  - Add a test that compares numbers and keywords in each catalog `mapping`/`diagnostic`/`transfer` against the item bank.
  - State that the lesson examples are the same for every arm and don't come from the catalog.

**2. High: the labels copy the main score input, so C's wins are close to circular** (`benchmark.json` grades vs. `catalog.json` `conceptual_fit`; `score_reference`)
- In the general-style cases, grades follow `conceptual_fit` almost exactly:
  - opportunity_cost: fit 3/2/1/2, grades 3/2/1/2 (identical).
  - marginal_analysis: fit 3/2/1/2, grades 3/2/1/1.
  - independence: fit 3/2/1/2, grades 3/2/0/0 (same order).
  - conditional_probability is the only group where they disagree (`cp-cards` fit 1, grade 2), and it is the only group where C loses to B in all 6 cases.
- Two of C's four score parts never vary:
  - Familiarity is 2 everywhere except the corrected cases.
  - `documented_prior_use` never fires because `sessions` is empty in every case.
- So C's ranking is essentially the author's own earlier relevance judgment.
- The preregistration says it was "written before selection scoring code", but the repository can't show that. At the start of this session `preregistration.json`, `selection.py` and `catalog.json` were all in the single initial commit, while `benchmark.json` (the grades) was untracked, so the grades were probably written with the fit values already in place.
- **Repair:**
  - Report the per-case rank correlation between fit and grades.
  - Present C's wins in non-baseline cases as a consistency check, not evidence.
  - Re-grade with the fit and tags hidden, or have someone other than the grader assign fit.
  - Reword the preregistration timing as "asserted, not verifiable".
  - Add cases that actually exercise familiarity and prior use.

**3. High: B's results are produced by alphabetical tie-breaking and planted affinities** (`arms()` in `evaluation.py`)
- In 21 of 25 ranked cases every affinity is 3. The top-5 cap then keeps items in ID order (bags, cards, commute, cooking, shopping) and always drops time, weather and story. This explains:
  - The large opportunity_cost C−B gaps (+0.46 to +0.48), because B loses `oc-time` and `oc-story`.
  - B winning all of conditional_probability, because alphabetical order happens to give bags, cards, shopping = grades 3/2/1, the ideal ranking.
- In the baseline_strength cases, affinity 5 is placed on exactly the grade-3 item.
- D has a similar problem: when there is no tag overlap (most cases), it is just reference-ID order.
- **Repair:**
  - Generate affinities independently of the grades and preregister how (for example, seeded random values, or several affinity patterns per objective).
  - Score B and D as expected nDCG over random tie orders instead of ID order.
  - Report how many cases were all ties.
  - Describe D as "ID order when overlap is 0".

**4. Medium-high: the headline mean hides the test-split result and counts duplicate variants** (`evaluate()` summary and REPORT.md; preregistration `generalization`)
- The test split gives C−B = −0.0503 (n=12); development gives +0.1363. REPORT.md shows only the pooled +0.0467.
- Variant pairs give the same result in every group:
  - corrected_familiarity equals general (0.19353057).
  - unknown_familiarity equals exclusion (0.13030754).
- opportunity_cost contributes 7 ranked cases while the other groups contribute 6. Weighting each concept group equally gives about +0.036.
- "Transfer across held-out concept groups" is the wrong term, because nothing is fitted or learned.
- **Repair:**
  - Lead REPORT.md with the test split and the equal-weight group mean.
  - Report how many distinct (objective, eligible set, grades) setups there are.
  - State plainly that C does not beat B on the held-out split.
  - Rename the generalization claim.

**5. Medium: recall can't reach 1 in some cases** (`positive_recall` in `evaluate()`)
- Recall divides by the number of positives, but at most 3 references are returned. The opportunity_cost cases have 4 positives, so their maximum is 0.75, and the mean mixes different ceilings.
- **Repair:** divide by `min(k, len(positive))`, or rename the metric and report each case's ceiling.

**6. Medium: the zero-violations gate mostly checks that one copy of the code matches another** (`oracle_eligible`; evaluation.md "separate eligibility oracle")
- The oracle re-implements `rejection_reasons` line for line, and arms B, C and D all draw from `candidate_pool`, so zero violations is nearly guaranteed.
- The two also differ on edition: the oracle tests whether `edition` is truthy, production tests `is not None`.
- **Repair:**
  - Add explicit expected outcomes to the benchmark (for example `forbidden_reference_ids` for progress-unknown, spoiler-blocked, edition-wrong and the excluded items) and gate on those.
  - Make the edition check identical in both.
  - Describe the oracle as a consistency check.

**7. Medium: the pilot estimand's weighting doesn't match its wording** (`_standardized_difference` and `analyze` in `pilot.py`; pilot.md "Analysis")
- Equal weight per stratum only equals "the mean among everyone randomized" when the strata are the same size. pilot.md says equal strata are only a target.
- REPORT.md leads with the complete-case estimate, although pilot.md makes the all-allocated bounds primary.
- **Repair:**
  - Either weight by each stratum's share of randomized participants (n_s/N) in both the estimate and the bounds, or rename the estimand "equal-weight stratum average".
  - Lead the report with the bounds.

**8. Medium: pilot order and form design** (pilot.md design section; `analyze`)
- "Half of each allocation block starts with economics" is impossible with blocks of 3.
- pilot.md says to report form and order distributions first, but `analyze()` doesn't report them, and concept order isn't in the analysis CSV at all.
- **Repair:**
  - Counterbalance order across pairs of blocks, or randomize order separately with balance within each stratum.
  - Add `concept_order` to the CSV.
  - Output form × arm × stratum and order × arm counts.
  - Validate X/Y values and that retention uses the other form.

**9. Medium: rubric errors** (pilot.md item bank)
- **Double counting:** the probability rubrics score "restricting to the group" and "denominator" separately, but they are the same decision. Using 60 costs about 3 of 4 points, while an economics mistake costs 1, so the two halves of the 0–8 score are weighted unequally.
- **Undefined point:** "A correct bare number gets only the arithmetic point", but no criterion is labelled as the arithmetic point.
- **Forms aren't parallel:** Form X probability hints at the distractor ("usar ou não usar 60"); Form Y and the baseline don't.
- **Missing definitions:** the `conceptual_errors` categories are never specified, and carry-forward is defined only for economics.
- **Repair:**
  - Restructure the probability criteria as conditioning set/denominator, numerator, value, and why the full total is excluded.
  - Give the score for 9/60 explicitly.
  - Define the bare-answer score.
  - Use identical prompt wording across forms.
  - List the error categories.
  - Add a carry-forward rule for probability.

**10. Low-medium: synthetic rows leak the missing outcome** (`synthetic_rows`)
- Withdrawn participants still get a `conceptual_errors` value computed from their hidden score, plus minutes, hints and context use.
- **Repair:** set these to missing when `immediate_score` is missing, and enforce that in `_validate`.

## Examined scope
- **Read:**
  - `selection.py`, `evaluation.py` (both before and after it was reformatted), `pilot.py`.
  - `data/preregistration.json`, `catalog.json`, `frozen_manifest.json`.
  - All 31 cases in `benchmark.json`: grades, which items are excluded or set to familiarity 0, and where affinity is 5.
  - `docs/evaluation.md`, `docs/pilot.md`.
  - `evidence/evaluation/{REPORT.md,summary.json,pairs.json}`, `evidence/pilot/analysis.json`.
- **Checked by hand:** the nDCG values in several cases match `pairs.json`; the pilot arithmetic and bounds are right; all six item answer keys are correct.
- **Not run:** no code, per your instructions.
- **Re-verify:** `evaluation.py` changed while I was reviewing. After the final edit, confirm the hash in `frozen_manifest.json` matches the file and regenerate `evidence/`.
