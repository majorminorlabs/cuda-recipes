# Package validation

Prepared on 2026-11-23 without new inference or hardware provisioning.

- All 12 numerical rows rebuild from the public raw llama-bench JSON and declared run roles. Means, sample standard deviations, sample arrays, flags, repetition counts, source commit and artifact identity are checked against the raw row.
- Four primary rows cover two Q4 artifacts × pp512/tg128, with three repetitions each.
- Four 0/8K depth rows have three repetitions. Four verified 128K/256K rows have one. Two incomplete initial depth attempts have no invented measurement.
- Fourteen context attempts include ten allocation failures and four successful short-generation checks. Classifications are checked against captured error/output text.
- All 274 compressed evidence files match their compressed/content hashes and byte counts. The manifest must cover the evidence directory exactly, without duplicates or missing files.
- The hardware manifest requires the two recorded RTX 3090 hosts and the artifact manifest requires the two Q4 files. Total GPU capacity is checked as 24,576 MiB.
- Path/credential checks inspect public metadata and decompressed evidence. Original source hashes are kept separately from public-content hashes.
- The overview and decode-depth PNG/SVG graphics use the recorded measurement IDs and exact data in `CHARTS/figure-data.json`. Images are inspected for labels, scales, layout and repetition/host caveats.

Run `scripts/validate.py`, `scripts/rebuild_measurements.py --check`, `scripts/summarize.py --check` and `shasum -a 256 -c SHA256SUMS` from this directory. Repository-level publication and checksum checks also apply. These checks validate packaging and provenance; they do not add repetitions or close the limits in `LIMITATIONS.md`.
