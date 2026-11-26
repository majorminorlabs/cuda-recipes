# Limitations

- One machine, one full sequence per configuration. No confidence intervals or broad engine ranking.
- Edge0 changes model packaging and routing. Results cannot isolate runtime effects from model changes.
- RAM caps use different operating-system mechanisms. Uncapped llama.cpp can use more host memory. These are not matched-memory comparisons.
- Magnitude prefill can reuse cache. Empty-request startup and earlier shared filler prefixes affect timing.
- Successful generation at long context does not establish general long-context quality. There are only two retrieval items.
- Quality categories are small, strict and format sensitive. The substitute set is not the separate 120-trial suite. Magnitude and Flash Next have no quality score.
- Edge0's 128K quality rejection reflects configured context capacity. Raon's retrieval token lengths are shorter than the nominal labels.
- Flash's stop after 60m48s is a timeout observation, not proof of an architecture failure or OOM. Missing and unattempted outcomes are not zeros.
- Raon worked on the KRAFTON branch only. The later stock build failed tensor validation; do not claim current upstream compatibility beyond the tested pairing.
- Source reports and selected quality evidence were curated for publication. Operational logs and transport records are excluded. Reproducing inference requires the pinned upstream model assets and runtimes; weights are not distributed here.
