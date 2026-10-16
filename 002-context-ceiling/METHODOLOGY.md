# Methodology

## Design and runtime

This is a fit + speed study only. The two pinned GGUFs and llama.cpp revision `620d2225cc436ab0b001e3200e590e3b286ef9ab` were used with CUDA for sm_86 on a single RTX 3090 24GB. Server flags were `--parallel 1 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja`; CPU layer offload was disabled. See the sanitized [hardware manifest](DATA/rtx3090-manifest.json).

## Context load sweep

The configured grid was 16,384, 65,536, 131,072, and 262,144 tokens, never exceeding the native maximum. Per model the grid was attempted ascending; after first failure, binary search found the largest passing 8,192-token multiple. A context counts as loaded only when `/health` returns HTTP 200 and every model layer is on CUDA. nvidia-smi sampled peak VRAM at 2 Hz or faster from launch through readiness or failure.

llama.cpp logs a dry-run fit pass before real allocation. Buffer parsing starts from the real allocation block associated with the first non-zero CUDA model-buffer line and excludes earlier fit diagnostics. This prevents dry-pass RS and compute values from being counted twice. Failed attempts retain only fields present in their real allocation diagnostics; missing fields are blank and explained in `error`.

## Speed by fill depth

llama-bench measured a 512-token prompt (`-p 512`) and 128 generated tokens (`-n 128`) at depths 0, 65,536, 131,072 and `ceiling90 = round(0.9 × model ceiling)`. A depth was skipped if depth plus 640 tokens exceeded that model's ceiling. Each depth used one llama-bench invocation and its own VRAM sampler. Three repetitions were collected at depth zero; one at every depth above zero. The context fill was synthetic.

Depth zero is shown as the observed three-run range; deeper points are single runs. Thus the deeper speed percentages are descriptive and have no replication-based uncertainty estimate.

## Comparison with 001

The driver was 610.57.04, versus 580.126.20 in CUDA Recipes 001. In addition, 002 speed was measured with llama-bench, whereas 001 used its task harness. The two studies' speed numbers are not the same measurement and should not be compared as if they were.

The first Nemotron 16K anchor attempt was excluded because our runner crashed while decoding logs. The runner was fixed and the retry completed; this was not a model failure.

## Cost and scope

The pod ran 0.867 GPU-hour from start through termination. At the advertised $0.50/hour RunPod RTX 3090 list price, the cost is estimated at about $0.43, not an invoice. Long-context quality and retrieval are out of scope.
