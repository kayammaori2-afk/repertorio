# Internal integration contract

Package is `repertorio`, CLI `repertorio`. Use Python >=3.11 and Pydantic v2.

Storage exports `Store(path: str | Path, profile: str)` and methods returning JSON-serializable dicts. Each method opens/closes its own SQLite connection. Server resolves profile from local configuration or token, never caller-provided identity.

The implemented SQLite schema is version 4. The portable profile format remains schema_version 1. Session delivery provenance is `client_reported_delivery`, with reported use marked self_report/tutor_report. Caller-supplied server_delivery or verified origin is rejected. HTTP mutation credentials also require read permission because responses and previews disclose scoped metadata. Known catalog references persist their repertoire links; unknown/historical references require explicit scoped repertoire IDs. Migration backfills resolvable legacy links and rolls back with recovery advice when links cannot be established.

- `get_profile()` returns `{schema_version: 1, repertoire: [...], evidence: [...], sessions: [...]}`.
- `save_item(item: dict, request_id: str, expected_revision: int | None = None)` returns the saved item with revision. Require expected_revision for updates. Create needs stable `id` from item.
- `record_evidence(evidence: dict, request_id: str)` returns saved evidence. Reject caller-supplied objective verification.
- `record_session(session: dict, request_id: str)` returns saved session with id.
- `export_profile()` returns versioned profile portable to another identity with original record provenance.
- `import_profile(payload: dict, request_id: str, dry_run: bool = True)` returns counts/conflicts or result. Atomic, merging equal IDs only when identical, conflicts otherwise. Re-import identical payload no-op.
- `import_csv(text: str, request_id: str, dry_run: bool = True)` delegates validated repertoire import.
- `prepare_delete(kind: str, ids: list[str])` returns confirmation token, scope, expires. Allowed kinds repertoire/evidence/sessions/all. All only with empty ids. Bind token to profile/revisions.
- `confirm_delete(token: str)` removes selection and affected derived records plus replay copies that could restore deleted data, rejects changed/expired/used tokens. Server requires delete scope on both methods.

Raise `ValueError` for input and conflict errors with useful safe messages. No raw SQLite errors exposed by tools. Agent can add domain exceptions subclassing ValueError.

Repertoire item common fields: `id`, `title`, `kind` (experience/book/film/series/anime/game), `status` (planned/started/completed/abandoned/unknown), `affinity` 0..5, `familiarity` 0..3, `progress` optional 0..100, `elements` list of confirmed strings, `excluded` bool, `source` string, `edition` optional string, `external_ids` dict. Stored values include revision and timestamps. Unknown familiarity default 0.

Evidence fields: `id`, `concept`, `activity_id`, `activity_version`, `help_received`, `result`, `origin` (self_report/imported/tutor_assessment/provisional), `assessor`, optional `summary`, optional `session_id`, timestamps. No automatic mastery score.

Selector exports `prepare_context(profile: dict, concept: str, objective: str = '', tags: list[str] | None = None, limit: int = 3) -> dict`. Profile repertoire shape as above. Return policy_version, catalog_version, references list, fallback and brief pedagogy. References have IDs, mapping, limitation, reason, source. No raw arbitrary imported prose in system guidance. Catalog uses confirmed repertoire item IDs (examples fixed everyday IDs and sources). Evaluation may expose additional helpers.

CLI expected commands `serve` (stdio default, http opt-in), `init-token`, `demo`, `doctor`, `evaluate --output DIR`, `pilot --output DIR`, `verify`, `export`, `import`, `delete`. Keep commands clear and use argparse if sufficient. Global `--db PATH`, `--profile ID`, `--allow-delete` for local operator. Tokens configuration via env/path only, never actual token as argument. Default data path OS user data directory or explicitly chosen location outside source tree.

Tests import package from editable project installation. Root owns pyproject and uv.lock. Agents coordinate added dependencies with root. Root creates environment. Run `<workspace>/work/tooling/Scripts/uv.exe run ...` in repository once ready. Do not run competing uv sync commands.
