# v0.1.0 release verification

The owner authorized license selection and public GitHub publication on 2026-11-16. The selected license is MIT for code, documentation and original bundled data. Repository: https://github.com/kayammaori2-afk/repertorio. Release: https://github.com/kayammaori2-afk/repertorio/releases/tag/v0.1.0.

The implementation and initial static reviews are documented in [verification.md](verification.md). Publication adds package license metadata, a complete LICENSE file, a revised README/Portuguese guide, public repository links, issue templates and a private security reporting channel. The core algorithms and storage behavior are unchanged.

`freeze-v4-license-publication` changes catalog rights text from pending to MIT and preserves the prior manifest as `data/freeze_history_v3.json`. No mapping, requirement, score, label or numerical ranking changes. Historical host transcripts retain the exact pre-license response they observed.

Release checks and their measured results are recorded in `evidence/publication/`. The release's SHA256SUMS file identifies the distributed source ZIP, wheel and sdist. The source archive retains frozen input bytes. The manual public-repository CI workflow targets standard Windows and Linux runners, with timeout, concurrency control and no automatic push/PR runs.

Limits remain explicit: no participant experiment, independent pedagogical validation, remote ChatGPT deployment, hosted service or PyPI publication. AI authorship and owner contributions remain described in [contribution.md](contribution.md).

The release review is [recorded here](../evidence/publication/review.md). Its manifest mismatch was repaired and the final 131-test gate passed. Follow-up improvements protect common export/credential filenames from accidental Git inclusion and make all host examples use explicit private database paths. The [fresh clean-wheel record](../evidence/clean-install.json) and [license/ranking checks](../evidence/publication/local-checks.json) identify the current artifacts. Historical review observations do not override these later execution records.
