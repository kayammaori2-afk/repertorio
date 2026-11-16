# Release verification

## v0.2.0

The owner explicitly authorized closing the Claude review, correcting findings, merging PR #1 and publishing v0.2.0. MIT remains unchanged. The independent other-family review and two closeouts are recorded under `evidence/v0.2/`; the final code gate is described in [verification.md](verification.md).

The release process binds the reviewed PR head, the merged tree, Windows/Linux CI, the exact installed wheel and twelve unchanged numerical artifacts in an external `release-manifest.json`. `SHA256SUMS` covers the source ZIP, wheel, sdist, empty pilot kit ZIP and manifest. The [v0.2.0 release page](https://github.com/kayammaori2-afk/repertorio/releases/tag/v0.2.0) is the source of publication status; uploaded assets are downloaded again and compared with their local hashes before completion is reported. Historical candidate checks remain labeled and do not identify the final wheel.

No human study or educational benefit is claimed. Pilot readiness still requires genuine human reviews, operational details, consent and participants. No remote ChatGPT endpoint, hosted service or package-registry publication is included.

## Historical v0.1.0 release verification

The owner authorized license selection and public GitHub publication on 2026-11-16. The selected license is MIT for code, documentation and original bundled data. Repository: https://github.com/kayammaori2-afk/repertorio. Release: https://github.com/kayammaori2-afk/repertorio/releases/tag/v0.1.0.

The implementation and initial static reviews are documented in [verification.md](verification.md). Publication adds package license metadata, a complete LICENSE file, a revised README/Portuguese guide, public repository links, issue templates and a private security reporting channel. The core algorithms and storage behavior are unchanged.

`freeze-v4-license-publication` changes catalog rights text from pending to MIT and preserves the prior manifest as `data/freeze_history_v3.json`. No mapping, requirement, score, label or numerical ranking changes. Historical host transcripts retain the exact pre-license response they observed.

Release checks and their measured results are recorded in `evidence/publication/`. The release's SHA256SUMS file identifies the distributed source ZIP, wheel and sdist. The source archive retains frozen input bytes. The manual public-repository CI workflow targets standard Windows and Linux runners, with timeout, concurrency control and no automatic push/PR runs.

Limits remain explicit: no participant experiment, independent pedagogical validation, remote ChatGPT deployment, hosted service or PyPI publication. AI authorship and owner contributions remain described in [contribution.md](contribution.md).

The release review is [recorded here](../evidence/publication/review.md). Its manifest mismatch was repaired and the final 131-test gate passed. Follow-up improvements protect common export/credential filenames from accidental Git inclusion and make all host examples use explicit private database paths. The [fresh clean-wheel record](../evidence/clean-install.json) and [license/ranking checks](../evidence/publication/local-checks.json) identify the current artifacts. Historical review observations do not override these later execution records.

## Executed public-source checks

Both Windows and Linux jobs passed in [manual CI run 43927397744](https://github.com/kayammaori2-afk/repertorio/actions/runs/43927397744), on source commit `aff0280b9dc325b334249403f7daea88926b22d0`. The [CI record](../evidence/publication/ci.json) lists each step. A fresh public clone installed the lockfile, ran the real two-process demo and reproduced eight evaluation outputs byte-for-byte. The [clone record](../evidence/publication/public-clone.json) identifies its commit. A final run on the tagged release commit is linked from the release receipt.

The original local development history remains local. Public history starts from the reviewed source snapshot and uses the owner's GitHub noreply identity. No private profiles, local environments or credentials are included.
