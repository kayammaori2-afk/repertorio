# Security scope

In v0.2, use `init-token` and `revoke-token` for coordinated registry updates. A `.lock` file serializes these writers; a busy operation fails before changing credentials. After a crash, stop initiating registry updates and confirm that all `init-token`/`revoke-token` processes for that registry have ended. Inspect the private registry and token files for the last completed operation. Only then remove the adjacent lock file (for `credentials.json`, exactly `credentials.json.lock`) and retry once. Do not remove the registry or token file, and do not remove a lock while another writer may be active; no timestamp alone proves staleness. Manual edits do not participate in this lock and must not run concurrently. Revoking the final credential leaves a valid empty deny-all registry; the old token file is not automatically removed. Private output rejects final-component symlinks/reparse points. Ancestor directories must still be trusted; these CLI helpers do not defend against a malicious same-user process replacing parent directories.

This release is for a trusted local operator. The HTTP service binds to loopback and authenticates each protected request. Credentials are local secrets and are excluded from source archives. Host and Origin validation addresses cross-origin requests and DNS rebinding. The server validates identity, scopes, payload bounds and record revisions independently of MCP annotations.

The database contains educational information. Another process with the same filesystem access can read it. OS account permissions and device encryption belong to the operator's environment. Prefer a private OS data directory and minimize stored answer summaries. No external telemetry is sent by the Repertorio server. The assistant provider may receive the context returned to its host. Check the provider's data controls before using real personal data.

Imported prose is untrusted data. The service does not execute it, retrieve arbitrary URLs or accept model-supplied filesystem paths. Structural separation and server tests do not establish the host model's resistance to prompt injection.

Deletion removes selected active content and affected derived/replay payloads as described by its preview. It retains hashed request markers to prevent retry resurrection; guessed profile/request IDs can be confirmed against those markers. Use random nonsemantic request IDs. See docs/data.md for the exact retention boundary. Deletion cannot retract copies in host conversations or user backups. SQLite free pages, filesystem snapshots and storage media may retain bytes. Use an appropriate device/backup lifecycle if physical erasure is required. Keep exported profiles private.

Local deletion is disabled unless granted in launch configuration. HTTP deletion requires the corresponding server-side scope. Preview tokens bind the selection and revision, expire and can be used once. They limit the operation. Human intent still depends on the host's approval flow or a supervised CLI operation.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/kayammaori2-afk/repertorio/security/advisories/new) for security findings. Include the affected version, a minimal reproduction using synthetic data and the expected impact. Do not put vulnerabilities, personal profiles or credentials in a public issue. Ordinary bugs can use the repository's issue tracker. This project does not promise a fixed response time.

## Release evidence

See evidence/dependency-audit.json for the advisory scan and docs/verification.md for executed defensive tests and review. A successful check is specific to its tested inputs and code revision. External deployment, compliance certification and human learning efficacy remain unverified.
