# Key findings

- Across 240 assignments, strict task success was **164/240 (68.3%)** on RTX 3090 and **155/240 (64.6%)** on RTX 5090. The paired difference (5090 minus 3090) was **−3.75 percentage points**, task-cluster bootstrap 95% CI **−8.75 to +0.83 pp**; the interval includes zero.
- Qwen exceeded Nemotron on both GPUs for this fixed suite: 3090 **89/120 (74.2%) vs 75/120 (62.5%)**; 5090 **84/120 (70.0%) vs 71/120 (59.2%)**. These comparisons are artifact-and-suite specific.
- The RTX 5090 ran faster. Median complete-trial latency for Nemotron/Qwen was **3.44/3.47 s** versus **5.68/5.37 s** on RTX 3090. Decode rates were **148.3/72.5 tok/s** versus **85.2/41.5 tok/s**.
- Paired binary outcomes agreed on **207/240 (86.25%)** assignments: 21 were 3090-only successes, 12 were 5090-only successes. Agreement does not imply identical text or tool traces.
- Peak measured VRAM was **21,339/16,481 MiB** (Nemotron/Qwen) on RTX 3090 and **21,865/16,514 MiB** on RTX 5090. Peak container RAM was **47.52/47.26 GiB** and **46.87/47.55 GiB**, respectively.
- Estimated rental for the two scored comparison runs was **$0.36 + $0.59 = $0.95** across **1.218 allocated GPU-hours**. The provider did not return a posted billing row for the corrected 5090 pod; this is a rate-times-uptime estimate, not an invoice.

Evidence: `DATA/paired-comparison.json`, paired run CSV and canonical per-GPU result JSON. See `RESULTS.md` for complete breakdowns and `LIMITATIONS.md` for interpretation.
