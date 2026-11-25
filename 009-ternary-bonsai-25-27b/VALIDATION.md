# Validation

Run `python3 scripts/validate.py` from this folder. It checks that both Bonsai arms have 120 trials, the combined trial CSV contains 240 records, reported strict counts agree with the frozen summaries, model digests have the expected length, the runtime manifest is present, and plotted values match the packaged quality and benchmark data. It also checks that all five PNG/SVG chart pairs exist. `SHA256SUMS` covers the packaged files.
