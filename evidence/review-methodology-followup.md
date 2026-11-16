# Independent static AI review

Reviewer: Claude Opus 5.5 through Claude Code, 2026-11-16. Read-only code/document review; not a human review or execution report. This report describes the state at its review time. Subsequent repairs are tracked in docs/verification.md.

I found four remaining issues: one is a correctness defect in the pilot item bank, two are about how the report presents its diagnostics, and one is a rubric criterion that doesn't match its prompt. The other repairs hold up. Nothing here needs humans, new labels or a new study.

## Remaining issues

**1. Form X economics item contains the typo "dezes7", which the overlap test can't see** (`data/pilot_items.json:30`, mirrored at `docs/pilot.md:28`)
- The prompt reads "realizar dezes7 custa 117". It should say "17", as the other forms write their counts as numerals ("finalizar 27", "restaurar 23").
- This text is in the frozen bank (`pilot_items.json` is hashed in `frozen_manifest.json`).
- The numeral test uses `\b\d+\b` (`tests/test_evaluation.py:136-138`). There is no word boundary between "s" and "7", so this quantity is never checked. The test passes without covering it.
- **Repair:**
  - Write "realizar 17 custa 117" in both files. "17" doesn't appear in the catalog or the shared lessons.
  - Re-freeze the bank.
  - Add a test that rejects mixed letter/digit tokens in prompts (`[^\W\d_]\d|\d[^\W\d_]`).
  - Add an answer-key test: the incremental cost equals the difference of the two totals in the prompt, and the numerator and denominator appear in the prompt.

**2. The tie-sensitivity results aren't summarized in REPORT.md, and C's own ties are never randomized** (`evaluation.py:179-253`, REPORT.md line 7)
- Mean nDCG for B falls from 0.827 with ID-order ties to 0.687 with random ties. D falls from 0.755 to 0.710.
- On the 12 held-out cases, B's random-tie mean is about 0.685 (my hand average of the per-case values in diagnostics.json). That is far below where B would need to be for C−B = −0.050 to stay negative.
- So the lead sentence "C does not beat B there" holds under the preregistered ID tie-break. It would very likely reverse under random ties. REPORT.md only points to diagnostics.json and doesn't say this.
- The diagnostic is also lopsided:
  - `prepare_context` also breaks ties by reference ID (`selection.py:186`).
  - Every concept has two references with fit 2.
  - In marginal analysis (shopping before time) and independence (bags before commute), ID order puts the higher-graded one first.
  - The effect is small, roughly 0.03–0.04 per affected case, but C keeps that advantage while B and D lose theirs.
- Keeping the fixed-order result primary is correct. The report just needs to say how fragile it is.
- **Repair:**
  - Randomize C's tied scores the same way.
  - Report random-tie means for B, C and D by split in REPORT.md.
  - Add one sentence: the sign of the held-out contrast depends on the tie order, and neither version addresses label circularity.

**3. The single fit/grade Spearman figure (0.39) understates the circularity** (REPORT.md line 7)
- The mean is pulled down by the four baseline-strength cases, which were built to disagree with fit and average about −0.41.
- In the 20 non-baseline cases:
  - The mean is about 0.55.
  - Fit order equals grade order exactly in 5/24 cases, all in opportunity cost.
  - 11 of the 20 have ρ ≥ 0.83.
- The pattern tracks the result:
  - Opportunity cost has the highest agreement (ρ = 1) and the largest C−B (+0.29).
  - Conditional probability has the lowest (ρ of 0.33 and −1) and C−B of −0.17.
- **Repair:** report ρ split by scenario (baseline-strength vs. other) and by concept group, next to that group's C−B. Also report `fit_equals_grade` as 5/24.

**4. The fourth probability criterion asks for something the prompt doesn't request** (`pilot_items.json:126`, `docs/pilot.md:48`)
- The prompt asks to "explique o grupo usado no denominador" (explain the group used in the denominator).
- Criterion 4 requires explaining "why the full population includes outcomes ruled out by the condition".
- An answer like "16/28 ≈ 0.571, because we only consider the 28 volcanic rocks" fully answers the prompt, but scorers could disagree about point 4.
- The economics prompt, by contrast, explicitly asks for its point-4 content ("explique como tratar o seguro").
- **Repair:** reword criterion 4 to something the prompt elicits: "explains that the stated condition restricts possible draws to that group, so the full total is not the denominator". Add one scoring example that earns the point and one that doesn't. The prompt can stay as it is, so the identical, no-distractor wording is kept.

## Repairs confirmed
- **v1 results preserved:** the v1 and current REPORT.md have identical nDCG values, C−B/C−D and B/D win lists. The `selection.py` and `catalog.json` hashes are the same in freeze-v1 and freeze-v2.
- **Report headline:** it leads with held-out −0.0503 (n=12), the equal-weight group mean 0.0364 (I recomputed it from the slices), and 13 distinct setups. "Learned transfer" wording is gone, and the preregistration timing is described as author-asserted.
- **Forbidden-reference gate:** all 31 cases carry `forbidden_reference_ids`. They are combined with the consistency check's violations, and a test shows the gate fires even when the oracle is replaced with one that always passes. The edition check is now `is not None` in both places, and the oracle is labelled a consistency check.
- **Recall:** each case's ceiling is exported and documented.
- **Pilot analysis:**
  - The estimand is renamed equal-weight, and the bounds use the same weighting.
  - The pilot REPORT leads with the bounds and shows form and order counts.
  - Validation enforces the alternate retention form, blank process fields when the outcome is missing, and error codes that match their count.
  - Order counterbalancing across pairs of blocks is feasible.
- **Rubric:** a full-total mistake and a fixed-cost mistake each now score 2/4, so the two halves are balanced.
- **Answer keys:** all six are arithmetically correct.

## Smaller residual limitations (not material)
- The overlap test covers only the catalog's `mapping`, `diagnostic` and `transfer` fields plus the lessons. The rendered packages also include title, limitation, prerequisites, the pedagogy and fallback text, and budget numbers. I found no digits in titles or limitations now; widening the test to every rendered field would keep it that way.
- The context keywords are English glosses checked against the English catalog, while the prompts are in Portuguese. For example, "telescope" never appears in Form X. `docs/pilot.md:15` accurately calls this a check of declared keywords, not semantic independence.
- `docs/evaluation.md:21` says "independently eligible", which contradicts the later "duplicate-policy consistency check" wording; one word to fix.
- `mean_positive_recall` in summary.json still averages across cases with different ceilings. It is documented and isn't in the report.
- The forms aren't equated: Y probability is 22/44 = 0.5, and Y economics is the only "decline" answer. This is disclosed, and forms are balanced across arms.
- The pilot REPORT bounds don't carry a "C−B, 0–8 scale" label.
- Shared-author circularity, the lack of independent preferences and labels, empty prior-use history, and no human data remain open, and the docs say so honestly.

**Scope:** I did a static read of the files you listed, plus `selection.py`, `catalog.json`, `benchmark.json`, `summary.json`, `freeze_history_v1.json` and the v1 report. I ran nothing and edited nothing, and I didn't check whether the manifest hashes match the current file bytes. Figures I derived by hand from diagnostics.json and summary.json are marked as approximate. This is not a human, subject-matter or psychometric review.
