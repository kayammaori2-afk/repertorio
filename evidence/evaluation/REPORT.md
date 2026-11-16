# Internal offline evaluation

Same agent authored catalog, cases and labels. No human or LLM efficacy evidence. Concept groups contain dependent variants. No statistical population inference or confidence interval.

Primary fixed-ID-order held-out split: C−B = -0.05030911 (n=12); C does not beat B under that tie rule. Equal-weight concept-group C−B = 0.03644356. The 25 ranked cases contain 13 distinct (objective, eligible-set, grade) setups; variants are dependent, and no fitting occurred.

Timing of the original preregistration is author-asserted, not independently timestamped. Catalog judgments informed the same author's labels; non-baseline wins chiefly check consistency. Mean fit/grade Spearman = 0.39029195. B has all-tied affinities in 21/25 cases; D has zero overlap in 16/25, making it ID order. Post-result random-tie diagnostics are in diagnostics.json; they do not repair label circularity.

A has no ranking metric. B/C jointly compare repertoire availability and policy; C/D use the identical eligible candidate set and k=3. All arms share the academic package and 12,000-byte ceiling.

| Arm | nDCG@3 | Denominator | Contexts/cases | Violations |
|---|---:|---:|---:|---:|
| A | None | 0 | 0/31 | 0 |
| B | 0.82745986 | 25 | 25/31 | 0 |
| C | 0.87419515 | 25 | 25/31 | 0 |
| D | 0.75540584 | 25 | 25/31 | 0 |

Post-result tie sensitivity randomizes equal ordering scores in B, C and D; all non-tied policy scores remain fixed. Main results above retain the original stable-ID rule.

| Split | B random-tie nDCG | C random-tie nDCG | D random-tie nDCG | C−B | Cases |
|---|---:|---:|---:|---:|---:|
| development | 0.68905678 | 0.88265399 | 0.70037417 | 0.19359721 | 13 |
| test | 0.68529562 | 0.83669799 | 0.72001065 | 0.15140236 | 12 |

The held-out C−B sign changes under this seeded random-tie sensitivity analysis. Neither tie rule addresses shared-author label circularity; this is a post-result diagnostic, not a new confirmatory test.

Fit equals grade in 5/24 correlation-applicable cases. Correlation and the corresponding fixed-order C−B are separated below.

| Cut | Mean fit/grade rho | Rho n | Fixed C−B | Cases |
|---|---:|---:|---:|---:|
| fit_scenario: baseline_strength | -0.40824829 | 4 | -0.53806885 | 4 |
| fit_scenario: other | 0.55 | 20 | 0.15812656 | 21 |
| concept: conditional_probability | -0.16666667 | 6 | -0.16901134 | 6 |
| concept: independence | 0.44725057 | 6 | -0.04734435 | 6 |
| concept: marginal_analysis | 0.44725057 | 6 | 0.06839312 | 6 |
| concept: opportunity_cost | 0.83333333 | 6 | 0.29373681 | 7 |

Paired C−B: 0.04673529; C−D: 0.11878931; n=25. These are descriptive differences for constructed cases.

B wins: opportunity_cost-baseline-strength, marginal_analysis-baseline-strength, conditional_probability-general, conditional_probability-baseline-strength, conditional_probability-excluded, conditional_probability-unknown, conditional_probability-corrected, conditional_probability-superficial, independence-baseline-strength
D wins: marginal_analysis-baseline-strength, conditional_probability-general, conditional_probability-excluded, conditional_probability-unknown, conditional_probability-corrected

Full case pairs, scenario/concept/split cuts, omission counts, context bytes and abstentions are in results.csv, pairs.json and summary.json. Latency is kept in latency.json with conditions in environment.json.
