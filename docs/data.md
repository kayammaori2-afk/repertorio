# Data and continuity

Each stored record has a stable ID, revision, creation/update timestamps and domain provenance. Repertoire covers kind, consumption status, affinity, familiarity, progress, spoiler limit, confirmed elements, explicit exclusion, edition and optional external identifiers. Updates require the last observed revision. An identical correction is a no-op. A concurrent update fails with a conflict rather than replacing a newer value.

Evidence identifies the activity and version, concept, help received, result and assessor. This release accepts self-report, imported information, tutor assessment and provisional inference. It has no controlled objective grading engine. Caller-supplied objective verification and verified usage are rejected. No durable mastery score is inferred.

`prepare_context` is read-only. Record a learning session explicitly after context delivery with `client_reported_delivery` provenance and record reported use with its source. Caller-reported delivery is not server attestation. Stored references track only the minimal history required for corrections and deletion. Full conversation transcripts are not enabled by the server. SQLite schema version 4 migrates earlier local schemas transactionally, normalizes missing fields and backfills catalog-reference dependencies. The portable profile schema remains version 1.

Current known context references automatically persist their implied repertoire IDs with the session, on record and import. This preserves deletion dependencies even if a later catalog removes that reference. An unknown reference or an explicitly different catalog version requires nonempty explicit repertoire IDs, validated within the same profile; their completeness is caller-declared, not independently attested. Legacy records that cannot establish these links fail migration transactionally with backup/recovery guidance. Existing data are preserved for correction rather than silently discarded.

## Export and restoration

JSON exports have schema_version 1 and repertoire, evidence and sessions arrays. Credentials and deletion confirmations are excluded. The schema file generated from the implemented models is `examples/profile.schema.json`. Imports are bounded to one MiB and 1000 records per collection. MCP wire envelopes allow two MiB so the largest supported profile fits inside an import call. The implementation also bounds persisted profile size to preserve restorable exports. All rows are validated and references checked before transaction commit. Identical IDs and values deduplicate. Different values at the same ID are conflicts. Preview the import before using `--apply`.

Use the CLI's export into a private file as a logical backup. Restore into an empty profile and compare its export. Copying an active SQLite database without its WAL can omit committed transactions. Prefer the logical export while the service is active.

## CSV repertoire

CSV requires unique `id,title` headers. Optional headers are `kind,status,affinity,familiarity,progress,spoiler_limit,elements,excluded,source,edition,external_ids,tags,language,revision,created_at,updated_at`. `elements` and `tags` contain JSON lists and `external_ids` a JSON object. Standard CSV quoting applies. `excluded` accepts true or false. Empty optional cells use the field's default. Affinity ranges from 0 to 5, familiarity from 0 to 3, and progress/spoiler limit from 0 to 100.

The sample `examples/repertoire.csv` is synthetic. Import it with `repertorio --profile sample import --input examples/repertoire.csv --format csv`, then use `--apply` after checking the preview. CSV covers repertoire. Use JSON for complete sessions/evidence and their provenance. CSV exports intended for spreadsheets must be treated as untrusted text because user-entered titles may begin with spreadsheet formula characters.

## Deletion

The local operator explicitly enables deletion with `--allow-delete`. HTTP credentials require delete scope. Preview the desired kind and IDs, show its affected derived records, then execute the returned confirmation token before it expires.

```sh
repertorio --profile student --allow-delete delete --kind repertoire --id everyday:shopping
repertorio --profile student --allow-delete delete --confirmation TOKEN_FROM_PREVIEW --yes
```

Changed revisions invalidate the preview. Tokens belong to the profile, expire and are single-use. Deletion retires replay payloads that could disclose removed records. Retry semantics after deletion intentionally prevent replaying removed content. Related sessions/evidence may be removed when retaining them would preserve the selected data. Review the complete preview.

Use random, opaque request IDs (for example UUID4) for every new mutation; reuse that ID only for retries of the same operation. Never encode names, record IDs or learning content in request IDs. To prevent a delayed retry from restoring deleted content, the database retains deterministic hashes of profile/request-ID pairs as retired markers. These no longer contain operation payloads or results, but a reader who guesses a pair can confirm that request existed. This is a deliberate residual retention limit, not anonymous storage or erasure of every trace. Profile namespaces themselves also remain. An authorized caller may observe the corresponding `deleted_result` response. Evidence `origin` is a caller-declared category unless explicitly described otherwise; `imported` is not an authenticated import attestation.

This affects active product data. Host transcripts, downloaded exports, backups, filesystem snapshots and storage-media remnants have their own retention. The operator controls them. Keep backups private and apply a retention period appropriate to the learner's needs.
