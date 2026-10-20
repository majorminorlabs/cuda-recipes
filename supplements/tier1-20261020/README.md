# Tier 1 evidence supplement — 2026-10-20

Added after the tagged publication: supporting source, protocols, scientific audits, and the small run records included in this supplement. Existing release tags and publication files are unchanged.

Files under `historical/20261020/` are retained historical variants, not replacements for the current published versions. Historical scoring results may have been superseded; consult the current study README and correction reports.

Machine-specific paths use `<HOME>` or `<WORKDIR>`. Recorded authentication arguments, real email addresses, and account/infrastructure identifiers are redacted. Reserved example-domain email addresses and synthetic benchmark fixture identities remain as test data. Redacted evidence preserves measurements; it is not a byte-identical reproduction of the private source.

Original SHA256SUMS records retained with the evidence describe the pre-redaction source files. The supplement SHA256SUMS file describes the added, sanitized copies.

CUDA 003 retains `_internal/scratchpad/progress.jsonl` as measurement-only timing evidence at the runner/test path. No pod, account or budget records are included. CUDA 004 `sampler.csv` is the original mixed-width telemetry stream (five- and eight-field records); it parses as CSV and is preserved without padding or rewriting measurement rows.

Reproduction limitation: The historical CUDA 003 test variant depends on dataset/planting-map paths outside its historical directory. Its two dataset identity checks cannot run successfully from that historical copy alone; the current CUDA 003 suite uses the published dataset and the retained timing evidence.

Default pytest discovery is restricted to the runnable public suites in `pytest.ini`. Archived original-run test modules are retained unchanged under `historical/tests/` and are excluded from default discovery. Active checks needing omitted archived inputs have explicit skip reasons. No omitted inputs were added.
