# Ternary Bonsai 2.5 27B on one RTX 3090

This study evaluates PrismML Ternary Bonsai 2.5 27B with the PrismML CUDA fork and stock llama.cpp. Its strict task scores are compared with the already published Qwen3.8 27B Q4_K_M results from study 001. The Qwen task suite was not rerun.

## Findings

- Bonsai PTQ1 plain passed 81/120 trials; the MTP quality arm passed 79/120. The reused Qwen result is 89/120.
- PTQ1 plain reached 94.536232 tok/s in the Prism build's F16 `llama-bench` tg128 row. The fresh Qwen row on that build was 45.972666 tok/s.
- Speculative decoding increased generation speed on a fixed three-prompt server comparison from 92.92596269119396 to 115.28064754265156 tok/s. This small comparison is separate from `llama-bench` and the task suite.
- Bonsai PTQ1 filled-context decode was measured at 76.433302 tok/s at 32K and 48.640977 tok/s at 128K with F16 KV; at 262K it was 18.878428 tok/s with Q8 KV.

See [KEY_FINDINGS.md](KEY_FINDINGS.md), [RESULTS.md](RESULTS.md), and [LIMITATIONS.md](LIMITATIONS.md) for definitions and full values. The matching Major Minor charts are in [CHARTS](CHARTS/README.md), with both PNG and outlined SVG versions.

## Reproduction

The 001 quality flags and frozen 40-task, three-repetition suite were retained. Both Bonsai arms used a current pinned PrismML build; the runtime differs from 001's build. Model revisions, hashes, runtime commits, flags, trial data, and benchmark output are recorded in this folder. No weights or raw model responses are included.

Run `python3 scripts/validate.py` to check the frozen suite inputs, trial counts, result manifests, and plotted values. Regenerate the graphics with `python3 scripts/make_charts.py` after installing `requirements-render.txt`. All paths in the public command record are normalized to `/study`.

## Credits and license

Ternary Bonsai 2.5 27B is from PrismML and is built on Qwen3.8-27B. Qwen is credited for the base model. Inference used llama.cpp from ggml-org and the PrismML fork. See [SOURCES.md](SOURCES.md) and the repository [NOTICE](../NOTICE.md). This study redistributes no model weights or runtime binaries.
