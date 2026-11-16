# Internal offline evaluation

Same agent authored catalog, cases and labels. No human or LLM efficacy evidence. Concept groups contain dependent variants. No statistical population inference or confidence interval.

A has no ranking metric. B/C jointly compare repertoire availability and policy; C/D use the identical eligible candidate set and k=3. All arms share the academic package and 12,000-byte ceiling.

| Arm | nDCG@3 | Denominator | Contexts/cases | Violations |
|---|---:|---:|---:|---:|
| A | None | 0 | 0/31 | 0 |
| B | 0.82745986 | 25 | 25/31 | 0 |
| C | 0.87419515 | 25 | 25/31 | 0 |
| D | 0.75540584 | 25 | 25/31 | 0 |

Paired C−B: 0.04673529; C−D: 0.11878931; n=25. These are descriptive differences for constructed cases.

B wins: opportunity_cost-baseline-strength, marginal_analysis-baseline-strength, conditional_probability-general, conditional_probability-baseline-strength, conditional_probability-excluded, conditional_probability-unknown, conditional_probability-corrected, conditional_probability-superficial, independence-baseline-strength
D wins: marginal_analysis-baseline-strength, conditional_probability-general, conditional_probability-excluded, conditional_probability-unknown, conditional_probability-corrected

Full case pairs, scenario/concept/split cuts, omission counts, context bytes and abstentions are in results.csv, pairs.json and summary.json. Latency is kept in latency.json with conditions in environment.json.
