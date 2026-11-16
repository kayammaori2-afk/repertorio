Static closeout from the supplied source only; no tools or tests run.

| Prior finding | Status | Assessment |
|---|---|---|
| 1. Editable blinding key | **Closed** | Analysis reconstructs assignments, failures and provenance, compares the key, verifies response/objective/rubric packets, and reports their hashes (`experiment.py:330–343,424–429`). |
| 2. Rubric outside prospective freeze | **Closed** | Preparation materializes the rubric; the manifest includes it; blinding copies the frozen material and analysis checks it. |
| 3. Empty consent accepted | **Partial** | Empty/whitespace consent is now rejected. The previously requested required-content check remains absent: arbitrary nonblank, marker-free text still passes when declarations are complete (`study.py:146–160`). |
| 4. Dangling destination symlinks followed | **Closed** | File writes preserve and inspect the final pathname before exclusive creation. Setup creates the requested directory exclusively without resolving its final symlink (`cli.py:90–103`; `setup.py:17–19`). Linux execution remains pending as stated. |
| 5. Concurrent credential updates | **Closed** | Initialization and revocation hold the same exclusive interprocess lock across registry mutation. Contention fails closed, addressing cooperating CLI writers within the stated scope (`cli.py:120–159`). |
| 6. Non-BMP TOML paths | **Closed** | Both interpreter and argument strings preserve Unicode characters; DEL is escaped. The supplied regression covers an emoji database path (`setup.py:25–28`). |
| 7. Response collection exceeds reader budget | **Closed** | Response and scoring-packet readers use the enlarged 128 MiB budget, accommodating the reported 500 × 20,000-character collection (`experiment.py:27,244,342`). |
| Conditional onboarding cutoff | **Closed** | Displayed references must belong to the evaluated candidate set; unevaluated tail entries cannot appear eligible (`onboarding.py:63–68`). |

The separately reported experience-status omission is also addressed in onboarding requirements, guidance and regression coverage.

**No new material blockers identified in these fixes within the stated scope.**