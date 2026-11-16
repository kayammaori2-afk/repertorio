# Prospective tutor-output comparison (v0.2)

This workflow prepares experiments. It does not call a provider, invent ratings or establish educational efficacy. The original selector benchmark and negative test result remain unchanged. Use `experiment` for tutor-output quality, `study` for pilot preparation, and `evaluate` for the frozen v0.1 selector comparison.

## Question and conditions

Does selected context improve tutor responses compared with a simple saved profile and the same teaching prompt? Primary contrast C−E; secondary C−B. A supplies academic context alone; B adds eligible favorites; C uses the unchanged selector; D uses the same eligible candidates ordered by tag overlap; E supplies confirmed non-excluded repertoire without curated mappings or ranking. E is a profile-plus-prompt baseline, not a reproduction of proprietary host memory.

All conditions share objective, academic evidence, system instruction, maximum 12,000 context bytes, chosen model/version and settings. Actual lengths differ and are recorded; token counts depend on the provider. This compares complete context strategies, not just ranking. D is the closer ranking ablation. No post-result weight tuning is included.

The default reuses 31 internally authored synthetic cases: **not independent validation**. For a new evaluation, obtain independent cases/preferences before responses. Supply `--cases FILE` with `origin` and `cases`; each case requires `id`, `concept`, `objective`, `tags`, `group_id`, and a versioned `profile`. No gold grades are accepted. Related variants must share a group. Schema checks cannot authenticate independence.

## Prepare and freeze

Use a private directory outside the checkout for actual data.

```sh
repertorio experiment prepare --output PRIVATE_DIR/comparison
# Optional: --cases PRIVATE_DIR/independent-cases.json
```

Complete `plan.json` with actual provider, exact model version, language, supported settings and pseudonymous case-author IDs. Default token/temperature settings are suggestions, not confirmed provider capabilities. Keep settings identical across conditions. Freeze prompts/rubric before collecting outputs and preserve old versions on changes.

```sh
repertorio experiment freeze --directory PRIVATE_DIR/comparison
```

The local manifest detects changes; it does not prove a prospective timestamp or external registration. Archive source commit/package checksum and environment alongside it. Never edit an old manifest to hide changes.

## Collect responses

Use a fresh model conversation per row of `jobs.json`, in seeded order. Send its `system` as instruction, the language from `plan.language`, and `context` as JSON data. No tools, browsing, cross-job memory or test answers. Do not send operator keys/gold labels. A host without settings control or conversation isolation supports only a technical smoke test, not a matched comparison.

Put one record for EVERY job in `responses.json`. A completed record has these fields (placeholders, not observations):

```json
{
  "job_id": "COPY_FROM_JOB",
  "status": "completed",
  "dataset_kind": "model_output",
  "provider": "EXACTLY_AS_FROZEN",
  "model_version": "EXACTLY_AS_FROZEN",
  "generation_settings": {"max_output_tokens": 800, "temperature": 0},
  "recorded_at": "ACTUAL_COLLECTION_TIMESTAMP",
  "text": "ACTUAL_UNEDITED_RESPONSE"
}
```

Failed records require `job_id`, `status: failed`, uniform `dataset_kind` and `failure_reason`. No favorable retries: prespecify retries or retain the first attempt and version any rerun. `synthetic_fixture` is reserved for artificial pipeline exercises. Metadata are operator declarations; the tool cannot prove provider behavior.

## Blind, score and analyze

```sh
repertorio experiment blind --directory PRIVATE_DIR/comparison --output PRIVATE_DIR/raters
repertorio experiment analyze --directory PRIVATE_DIR/comparison --ratings PRIVATE_DIR/ratings.csv --packet PRIVATE_DIR/raters --output PRIVATE_DIR/analysis.json
```

Give each rater only `responses-for-raters.json`, `objectives.json`, `RUBRIC.json` and their own `ratings-template.csv`. Operator keys stay separate. Labels, selection scores and gold grades are omitted, but response style/content can reveal conditions: masking is partial. The same two distinct raters score every completed response independently. Merge sheets without deleting disagreements. Author IDs are rejected; human/AI kinds are declared, not authenticated. AI scores are not expert validation.

Four 0–3 criteria: correctness, objective fit, appropriate analogy limits (accurate direct teaching can earn full credit), and an unassisted transfer question. Train reviewers on separate examples and review the rubric with an expert. Averaged ordinal ratings are not calibrated learning effects.

Analysis reports C−E first, then C−B/D/A, per-case differences, equal-weight group averages, failed jobs grouped by arm, planned/paired denominators, excluded case IDs per contrast and exact criterion agreement. Missing pairs are excluded, never zero-imputed; examine failure patterns. No population intervals or superiority claims are supported by this tiny dependent sample. One response per condition does not estimate stochastic model variation; independent repetitions require a new prespecified analysis version.

Automated fixtures validate packet generation, budgets, omission of explicit condition metadata, no-overwrite behavior, freezes, provenance consistency, job accounting, scoring and arithmetic. They do not establish independent annotation, tutor quality or human learning.

The rubric is materialized before collection and included in the input freeze. Analysis reconstructs the blind assignments, failures and declared provenance from frozen jobs and response records; it verifies the actual response/objective/rubric files supplied to raters. This detects inconsistent local edits, not replacement of an entire archive or false statements about what raters saw. Responses allow up to 20,000 characters each and 128 MiB per collection (up to 100 cases × 5 conditions); other research JSON inputs retain an eight-MB limit. Preparation checks the actual indented UTF-8 sizes before creating a directory. Freezing requires an empty response file and no blinding key; these guards still cannot prove collection timing against a dishonest operator.
