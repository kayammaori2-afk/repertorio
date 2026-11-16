# Adult feasibility pilot: protocol v3 after follow-up (not recruited)

This is a prepared protocol, original item bank and executable analysis demonstration. No participant was contacted, no lesson was delivered by an LLM, and no human outcome was observed. Expert and institutional/ethics review are pending. Artificial outcomes must never appear in a learning-effect chart without an explicit synthetic label.

## Question and design fixed before recruitment

The primary hypothesis is that structured context (C) improves unassisted transfer compared with favorites (B). A receives the same academic package without repertoire. Randomize individual consenting adults to A/B/C, using concealed computer-generated blocks of three within low/high baseline skill strata (baseline total 0–4 / 5–8). Keep the allocation list inaccessible to scorers. The implementation's reproducible seed 20261116 is for simulation only; generate and privately retain a fresh allocation seed before actual recruitment. Randomization must occur after eligibility and baseline scoring.

Plan 36 adults (12/arm) as a **feasibility sample**, not a powered effectiveness study. Include age 18+, ability to consent and read the study language, and no prior participation. Record prior exposure to the tested concepts; exclude advanced expertise using a prespecified screening question and threshold chosen with the reviewer before recruitment. Record the number screened, eligible, consenting, randomized, withdrawing and completing. Do not replace randomized dropouts. Equal-sized strata are a recruitment target, not permission to change allocation after viewing outcomes.

Use one tutor model/version, identical system instructions, generation settings and maximum context budget across conditions. The actual provider, immutable model version, settings, language, dates, equipment and item-bank hashes are **pending fields that must be completed and frozen before recruitment**. No paid calls are required by this software. If the version changes mid-pilot, stop new allocation, record a deviation, and decide a separate cohort before examining outcomes. A/B/C use the offline definitions in evaluation.md; primary contrast C−B, A comparisons exploratory.

Two 8-minute lessons cover marginal analysis and conditional probability. Counterbalance concept order across pairs of allocation blocks: one block starts with economics and the next with probability, so each arm within a stratum receives each order once per pair. Each block still contains three allocations, one per arm. Assign immediate form X/Y in a separate balanced schedule within arm/stratum, not by the participant's outcome. The simulation uses three blocks per form and alternates concept order; actual order/form schedules must be concealed and frozen before recruitment.

The common academic lessons are original **wind-tunnel calibration** and **wildlife observation** examples in `data/pilot_items.json`, identical in every arm and separate from the repertoire catalog. A receives these academic lessons alone; B and C additionally receive their respective context packages. Catalog diagnostic/transfer questions are part of that exposure and must never reuse a test item. The rewritten item bank's contexts and visible numeric literals differ from catalog mapping/diagnostic/transfer content and the common lessons. A mechanical overlap test catches literal-number and declared-keyword reuse; it cannot certify semantic independence or equal difficulty.

Deliver each arm's context immediately before the respective lesson. Limit to two optional graduated hints per lesson, use the same feedback policy and no test item in instruction. Record duration, hints, whether context was delivered and whether it was actually used (observer rubric plus provenance). Delivered context is not proof of use. If ignored, retain the participant in the allocated arm and describe nonadherence; per-protocol results may only be labeled exploratory.
Immediately afterward, close the tutor and give **two new problems, without assistance**, one per concept, maximum 10 minutes total. Primary outcome is the total 0–8 score. Randomize immediate form X/Y within each arm/stratum and use the other form at retention, seven days later (window ±2 days), again without assistance. Use different real-world contexts from the lesson. There is no condition crossover, reducing carryover; order and form are recorded. Avoid feedback on the immediate test until retention is complete. Ask and record intervening study exposure at retention.

## Original parallel items and rubric (bank v3 after follow-up)

The original v1 bank overlapped catalog examples and was replaced after independent review, before any recruitment. The authoritative machine-readable bank is `src/repertorio/data/pilot_items.json`, copied by the pilot command. This is an unvalidated parallel-form proposal, not psychometric equivalence. Expert review must check difficulty and leakage across every exposed prompt before recruitment.

**baseline-economics (4 points).** Um estúdio já pagou 103 pelo seguro. Finalizar 26 faixas de áudio custa 54; finalizar 27 custa 61. Um cliente oferece 13 pela faixa adicional, sem outra consequência. Deve finalizar a faixa adicional? Mostre o custo e o benefício adicionais e explique como tratar o seguro.

Answer: {"incremental_cost": 7, "incremental_benefit": 13, "net": 6, "decision": "accept", "fixed_cost": "unchanged"}.

**X-economics (4 points).** Um observatório já pagou 127 pelo seguro. Realizar 16 sessões de observação custa 106; realizar 17 custa 117. Um grupo oferece 19 pela sessão adicional, sem outra consequência. Deve realizar a sessão adicional? Mostre o custo e o benefício adicionais e explique como tratar o seguro.

Answer: {"incremental_cost": 11, "incremental_benefit": 19, "net": 8, "decision": "accept", "fixed_cost": "unchanged"}.

**Y-economics (4 points).** Um arquivo já pagou 139 pelo seguro. Restaurar 22 fitas custa 146; restaurar 23 custa 159. Um cliente oferece 10 pela fita adicional, sem outra consequência. Deve restaurar a fita adicional? Mostre o custo e o benefício adicionais e explique como tratar o seguro.

Answer: {"incremental_cost": 13, "incremental_benefit": 10, "net": -3, "decision": "decline", "fixed_cost": "unchanged"}.

**baseline-probability (4 points).** Uma reserva contém 88 árvores, das quais 32 estão na encosta. Entre as árvores da encosta, 14 produzem frutos. Uma árvore é sorteada uniformemente; sabemos que está na encosta. Qual é a probabilidade de produzir frutos? Mostre a fração, calcule o valor e explique o grupo usado no denominador.

Answer: {"numerator": 14, "denominator": 32, "value": 0.4375, "excluded_total": 88}.

**X-probability (4 points).** Um museu possui 104 amostras, das quais 28 são rochas vulcânicas. Entre as rochas vulcânicas, 16 são magnéticas. Uma amostra é sorteada uniformemente; sabemos que é uma rocha vulcânica. Qual é a probabilidade de ser magnética? Mostre a fração, calcule o valor e explique o grupo usado no denominador.

Answer: {"numerator": 16, "denominator": 28, "value": 0.5714285714285714, "excluded_total": 104}.

**Y-probability (4 points).** Um laboratório possui 116 tecidos, dos quais 44 são de algodão. Entre os tecidos de algodão, 22 são tingidos. Um tecido é sorteado uniformemente; sabemos que é de algodão. Qual é a probabilidade de ser tingido? Mostre a fração, calcule o valor e explique o grupo usado no denominador.

Answer: {"numerator": 22, "denominator": 44, "value": 0.5, "excluded_total": 116}.

Use the same four separate one-point criteria within each domain for baseline, X and Y. Economics: correct incremental cost; identifies the incremental benefit and compares it with the stated increment; decision follows that comparison; explains why insurance is unchanged. Probability: correct conditioning group/denominator (one criterion); correct favorable count within it; evaluates the displayed fraction; explains that the stated condition restricts possible draws to the named group. Saying that only this group is considered is sufficient; no separate discussion of the full total is required. Both domains therefore have a 4-point maximum.

A bare correct probability gets the value point only; a displayed correct fraction without prose gets denominator, numerator and value points. Economics bare yes/no gets only the decision point if correct; the other points need working/explanation.

Probability: an incorrect denominator loses the denominator point, but a correct numerator and correct arithmetic of the stated fraction can earn their points; incorrect full-population reasoning loses the explanation point. A full-total answer such as 16/104=0.1538 receives 2/4 if arithmetic is shown and no correct conditioning explanation is present. A correct fraction without decimal counts as an exact value. Economics: preserve the decision point if it follows the stated incremental comparison; do not award an incorrect cost point.

All probability prompts use identical instructions without selectively naming a distractor. Exact fractions count as correct values; accept decimals within 0.001. Score errors by criterion, not by how many times a misconception is repeated. Examples: for form X, an answer `16/104 = 0.1538` with no correct conditioning explanation earns numerator and arithmetic points (2/4), but no denominator or explanation points; a bare `0.5714` earns 1/4; `16/28` without prose earns 3/4.

For the explanation point, “16/28 ≈ 0.571, because we only consider the 28 volcanic rocks” earns the point: it links the condition to the restricted group. “16/28 ≈ 0.571, because 28 is written in the question” does not: it gives no conditioning reason. This interpretation matches the prompt asking for the group used in the denominator.

Conceptual-error codes, recorded separately from scores: E_FIXED_INCLUDED: unchanged payment added to incremental cost; E_TOTAL_OR_AVERAGE: total or average cost used instead of change; E_COMPARISON: incremental benefit/cost compared incorrectly; P_DENOMINATOR: conditioning group wrong; P_NUMERATOR: favorable count outside conditioned group; P_ARITHMETIC: calculation of stated fraction wrong; P_CONDITION_EXPLANATION: claimed conditioning leaves full population eligible. Each error category can occur at most once per participant test; multiple distinct categories are retained. Scorers record codes separately from the score. Missing tests have missing error counts, never inferred from hidden synthetic scores.

Two trained scorers see participant code, form and response, with condition, repertoire and tutor transcript hidden. Score independently; retain original scores and adjudication. Resolve disagreement by the named criterion, then a third blinded reviewer if unresolved. Tied scores remain tied; time is not a tiebreaker. Record descriptive agreement. Do not show the key before retention. Original responses and error codes require actual observation; never reconstruct them from a total score.

## Analysis and missingness

The unit is the randomized adult. The estimand is the equal-weight average of the C−B mean immediate transfer-score contrast in each prespecified baseline stratum under allocation. It targets a 50/50 low/high stratum mix, even when actual recruitment is imbalanced; it is not the sample-weighted mean among all randomized participants. Report arm totals, attrition, deviations and form/order distributions first. Retain assignment even if the context was ignored or the lesson ended early. The primary all-allocated estimand is not point-identified when outcomes are missing without assumptions: report worst/best bounded differences for scores in [0,8]. Lead the report with these all-allocated bounds. Also report a secondary complete-case standardized estimate under missing-at-random within arm/stratum, explicitly stating that assumption. Missing is not a zero score. The artificial withdrawals have missing duration, hints, context-use and conceptual-error values; no hidden synthetic outcome is recoverable from those fields. Real observed process data may be retained in a protected log when collected before dropout, but this demonstration conservatively leaves them missing in its analysis CSV.

The script provides a percentile bootstrap interval from 2,000 resamples of observed participants within arm/stratum (fixed simulation seed). It describes uncertainty conditional on this model and sample; small cells can make coverage poor. It is not a definitive confirmatory test. No p-value, efficacy declaration or multiple-testing claim is planned. Repeat the same descriptive analysis for retention; report time, hints, conceptual errors and context use separately. Analyze form or adherence sensitivity descriptively only. Keep deviations and withdrawals in the data; record reasons without demanding sensitive explanations.

Run the artificial demonstration:

```console
repertorio pilot --output evidence/pilot
python -m repertorio.pilot --input evidence/pilot/synthetic.csv --output evidence/pilot-reanalysis
```

Both outputs must be marked synthetic. `synthetic_rows()` includes balanced allocation, mixed outcomes, two missing primary outcomes, four missing retention outcomes, ignored context and protocol deviations. The CSV can be replaced by consented, reviewed study data only after completing the pending protocol fields. Set every row's `dataset_kind` to `human` only for actual human observations; the script checks consistent provenance and never converts simulation into observation. The analysis code has not been validated for a different trial design, clustered assignment or repeated condition crossover.

## Data dictionary and privacy

| Field | Meaning |
|---|---|
| dataset_kind | `synthetic` or `human`, uniform within a file |
| participant_id | random pseudonym, unique per randomized adult |
| stratum / block / arm | baseline low/high, concealed allocation block, A/B/C |
| baseline_score | unassisted 0–8 before allocation |
| immediate_form / retention_form | X or Y; validated alternate at retention |
| concept_order | economics_first or probability_first; counterbalanced across block pairs |
| immediate_score / retention_score | adjudicated 0–8, empty for missing |
| missing_reason / retention_missing_reason | concise non-sensitive missingness code |
| minutes / hints | lesson duration and count of hints |
| context_delivered / context_used | Boolean; delivery and observed/report-based use are separate |
| conceptual_errors / error_codes | count of distinct observed rubric categories and pipe-separated codes; missing/empty when no test observed |
| model / model_version | actual tutor model identifiers; simulation uses NONE_SYNTHETIC |
| deviation | concise implementation deviation, empty when none |

For the real pilot, keep a separate protected linkage/consent file; never put contact information or identifying repertoire in this analysis CSV. Add dates, retention interval, intervening exposure, scorer IDs and scoring adjudication in a protected study log; record provenance of context-use observations. Obtain applicable institutional/ethical approval and informed consent before recruitment. Explain that the host/provider may receive lesson context and that participation and withdrawal are voluntary. Set a retention schedule before consent (proposal: destroy identity linkage after follow-up/contact needs end; retain deidentified research records for 90 days unless approved institutional policy requires otherwise). Do not claim this proposal is legal compliance. Store responses only as needed for blinded scoring, control access, and disclose limits on removing already aggregated or downloaded copies. Specialist review, actual recruitment and efficacy remain pending.
