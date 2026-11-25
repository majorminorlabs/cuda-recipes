# CUDA Recipes 008 update: DSpark speculative decoding on one RTX 3090

Measured 2026-11-24. This appendix adds DSpark drafter tests to [CUDA Recipes 008](../). The original 008 measurements, files and corrections are unchanged.

Inkling 2 Mini UD-Q4_K_M ran in `llama-server` on one 24GB RTX 3090 with and without the DSpark drafter. Two builds were tested: Unsloth's prebuilt release `b12675-mix-d14fe45` and mainline llama.cpp at merge commit `33aeb17f85869279e3821f746bc645357139bc2c`. Every drafter ratio below divides by the no-drafter arm of the **same build**, sampler and length. None of them use the historical 008 `llama-bench` figure (59.106860 tok/s) as a denominator.

336 requests completed across 28 cells. Each cell has four prompts with three repetitions each. No request failed, ran out of memory or was discarded.

## Results

Rates are server-reported generated tok/s. Each cell mean is the arithmetic mean of 12 per-request rates. Prose tables round tok/s to two decimals and ratios to three; exact values are in [results-summary.json](results-summary.json) and every request is in [results-per-run.json](results-per-run.json) / [results-per-run.csv](results-per-run.csv). Acceptance is pooled: accepted draft tokens divided by drafted tokens across the cell's 12 requests.

### Unsloth b12675, default 0.50 GB drafter, greedy, 128 tokens

| n-max | Mean tok/s | Ratio vs off | Pooled acceptance | Peak sampled MiB |
|---|---:|---:|---:|---:|
| off | 81.08 | 1.000 | | 16,742 |
| 1 | 77.64 | 0.958 | 0.742 | 18,174 |
| 2 | 86.36 | 1.065 | 0.624 | 18,184 |
| **3** | **89.57** | **1.105** | 0.539 | 18,188 |
| 5 | 84.69 | 1.044 | 0.399 | 18,194 |
| 7 | 78.05 | 0.963 | 0.294 | 18,202 |

### Mainline 33aeb17, same 0.50 GB drafter bytes, greedy, 128 tokens

| n-max | Mean tok/s | Ratio vs off | Pooled acceptance | Peak sampled MiB |
|---|---:|---:|---:|---:|
| off | 59.83 | 1.000 | | 18,274 |
| 1 | 71.45 | 1.194 | 0.695 | 19,718 |
| **2** | **79.72** | **1.332** | 0.593 | 19,722 |
| 3 | 77.64 | 1.298 | 0.520 | 19,726 |
| 5 | 75.42 | 1.261 | 0.378 | 19,732 |
| 7 | 66.51 | 1.112 | 0.299 | 19,740 |

Best short-run n-max on this card: 3 for the Unsloth build, 2 for mainline.

### Both samplers and lengths

| Build | Sampler | Tokens | Off tok/s | Drafter | On tok/s | Ratio | Acceptance |
|---|---|---:|---:|---|---:|---:|---:|
| Unsloth | greedy | 128 | 81.08 | n-max 2 | 86.36 | 1.065 | 0.624 |
| Unsloth | temp 1 | 128 | 71.88 | n-max 2 | 74.24 | 1.033 | 0.558 |
| Unsloth | greedy | 1024 | 79.20 | n-max 2 | 86.66 | 1.094 | 0.619 |
| Unsloth | temp 1 | 1024 | 70.51 | n-max 2 | 72.84 | 1.033 | 0.575 |
| Unsloth | temp 1 | 128 | 71.88 | n-max 3 (exploratory) | 73.28 | 1.020 | 0.475 |
| Unsloth | greedy | 1024 | 79.20 | n-max 3 (exploratory) | 93.23 | 1.177 | 0.532 |
| Mainline | greedy | 128 | 59.83 | n-max 5 | 75.42 | 1.261 | 0.378 |
| Mainline | temp 1 | 128 | 54.42 | n-max 5 | 61.97 | 1.139 | 0.326 |
| Mainline | greedy | 1024 | 58.74 | n-max 5 | 84.90 | 1.445 | 0.485 |
| Mainline | temp 1 | 1024 | 53.92 | n-max 5 | 60.17 | 1.116 | 0.334 |

The two n-max 3 rows were added after the 128-token sweep picked n-max 3 and are exploratory. Mainline at 1024 tokens was only tested at n-max 5, so 5 is the tested setting there, not a measured optimum.

### Older 0.40 GB drafter file (optional, Unsloth build only)

`dspark-Inkling-2-Mini-Q8_0_Old.gguf` is a separate, smaller drafter file from the same Unsloth repository, distinct from the default `dspark-Inkling-2-Mini-Q8_0.gguf`. It was tested only on the Unsloth build at greedy 128 tokens and is kept out of the default-file sweep above.

| File | n-max | Mean tok/s | Ratio vs Unsloth off (81.08) | Pooled acceptance | Peak sampled MiB |
|---|---|---:|---:|---:|---:|
| Old 0.40 GB | **2** | **93.15** | **1.149** | 0.624 | 17,376 |
| Old 0.40 GB | 3 | 90.03 | 1.110 | 0.539 | 17,380 |

The old file was faster than the default file at both n-max values, with the same pooled acceptance, and peaked about 800 MiB lower.

### Prompt dependence

Per-prompt means (three repetitions each) are in `results-summary.json`. The B-tree explanation prompt slowed down in every Unsloth greedy drafter cell, including the best one: 81.52 off versus 71.23 at n-max 3 for 128 tokens, and 79.08 versus 68.61 at n-max 3 for 1024 tokens. At temperature 1, Unsloth n-max 2 slowed B-tree at 128 tokens (71.72 to 60.79) and Go retry at 1024 tokens (70.49 to 63.97). Mainline n-max 5 at temperature 1 slowed B-tree at 128 tokens (54.58 to 45.04) and Go retry at 1024 tokens (54.02 to 51.19). The refactor prompt gained most often, up to 112.51 versus 81.09 on Unsloth greedy n-max 3.

### Same-build `llama-bench` check (separate metric)

For context only, Unsloth b12675 `llama-bench` with the historical 008 flags measured pp512 2306.679173 and tg128 83.770313 tok/s (three repetitions; [build-comparison.json](build-comparison.json)). It is a different build and host from the historical 008 run (pp512 1411.470954, tg128 59.106860), so the difference is not attributable to the build alone. It is also a different metric from the server arms and is never a drafter denominator.

## Setup

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 3090, 24,576 MiB, driver 595.112.07, one GPU |
| CUDA compiler | 12.8.93 |
| CPU / OS | AMD EPYC 7763 (32 vCPUs allocated), Ubuntu 24.04.3 LTS |
| Unsloth build | release `b12675-mix-d14fe45`, binary `build 12675, commit add07b393`, GNU 11.4.0 |
| Mainline build | `33aeb17f85869279e3821f746bc645357139bc2c` (build 12720), Release, CUDA arch 86, GNU 13.3.0 |
| Target | `Inkling-2-Mini-UD-Q4_K_M.gguf`, 16,610,544,608 bytes (same file as the 008 base) |
| Default drafter | `dspark-Inkling-2-Mini-Q8_0.gguf`, 503,889,952 bytes |
| Old drafter | `dspark-Inkling-2-Mini-Q8_0_Old.gguf`, 402,278,560 bytes |

SHA-256:

```text
78fcedcf93c5d1bfe83e225513b71392bb52259be0eaa5f8899c856a2e5834ae  Inkling-2-Mini-UD-Q4_K_M.gguf
3da00cf7c31bbe5662b3c0d373ecf782d74d32ef43990acc158ce60c2add72e0  dspark-Inkling-2-Mini-Q8_0.gguf
2ec78510da837e8fc3be54a14757a0c5fbd2d8d9e85a0d92853fafdf674f3773  dspark-Inkling-2-Mini-Q8_0_Old.gguf
```

Full hashes, sources and the `Mainline_Support` copies are in [models.json](models.json). The mainline runs loaded the `Mainline_Support` copy of the drafter, which has the same bytes and hash as the default file. Hardware and build records are in [systems.json](systems.json). All cells ran on one host.

Peak memory is sampled every 0.2 s during each request, so short spikes can be missed. The highest sample was 18,202 MiB on the Unsloth build and 19,993 MiB on mainline (greedy, 1024 tokens, n-max 5).

## Method

- **Workload.** Four prompts in [tasks/](tasks/): sorted-list merge code, B-tree explanation, messy-function refactor and Go retry-with-jitter code. Each is rendered with the model chat template (`--jinja`, `/apply-template`); rendered templates are in [templates.json](templates.json).
- **Requests.** Non-streaming native `/completion` with `n_predict` 128 or 1024, `cache_prompt: false`, `ignore_eos: true`. Bodies are in [requests.json](requests.json).
- **Fixed lengths.** EOS was suppressed so both arms generate exactly the requested token count. These are fixed-length decode throughput tests, not organic completion lengths. Every request generated its full token count.
- **Server.** Context 16,384, `-ngl 99`, `-ngld 99` for the drafter, 8 threads, batch 2048 / ubatch 512, F16 K/V, flash attention on, one parallel slot. A fresh server was started for each cell; the cache was empty at the start of every request.
- **Sampling.** Greedy: temperature 0, top-k 1, top-p 1, min-p 0. Temperature 1: top-k 0, top-p 1, min-p 0. Seeds 4242, 4243 and 4244, matched across arms.
- **Order.** Within a cell, the four prompts ran in lexical order for repetition 1, then 2, then 3. Cells ran sequentially: the Unsloth primary matrix and sweep, the exploratory and old-file cells, the `llama-bench` check, then the mainline build and its cells.
- **Metrics.** Generated and prompt tok/s are the server's native timing fields ([native-timings.jsonl](native-timings.jsonl)), not client wall time. Wall time is retained. Off arms report no draft counters, and none are filled in.

Drafter cells add these flags to the no-drafter command:

```sh
-md "$DRAFTER" --spec-type draft-dspark --spec-draft-n-max N -ngld 99
```

The no-drafter server command for greedy cells:

```sh
llama-server -m "$MODEL" --jinja -ngl 99 -c 16384 -t 8 -b 2048 -ub 512 \
  -ctk f16 -ctv f16 -fa on --temp 0 --top-p 1.0 --top-k 1 --min-p 0.0 \
  --host 127.0.0.1 --port 8080 --parallel 1
```

Temperature 1 cells use `--temp 1 --top-k 0`. Every cell's exact argv, the build commands and download commands are in [commands.json](commands.json). The full settings are in [protocol.json](protocol.json).

### Replay one request

Start a local server with the exact argv for one cell from `commands.json` (`cells`), with your own model paths. Then send a body for that same cell from `requests.json`. The cell, prompt, repetition (seed) and length must all match the running server; a body from another cell measures a different configuration.

```python
import json, urllib.request

CELL, TASK, REP = "unsloth-greedy-n128-drafter-nmax3-original", "03-refactor", 1

entry = next(r for r in json.load(open("requests.json"))
             if (r["cell"], r["task"], r["rep"]) == (CELL, TASK, REP))
req = urllib.request.Request("http://127.0.0.1:8080/completion",
                             data=json.dumps(entry["request"]).encode(),
                             headers={"Content-Type": "application/json"})
timings = json.load(urllib.request.urlopen(req))["timings"]
print(entry["request"]["seed"], entry["request"]["n_predict"], timings["predicted_per_second"])
```

Compare `predicted_per_second` with the matching row in `results-per-run.json`. Restart the server between cells, as the study did.

## Limits

- **Speed only.** No quality, accuracy, recall or long-context evaluation was run. These results say nothing about whether outputs are good.
- **Greedy outputs differ.** With drafting on, greedy output text was not bit-identical to the off arm. Only 12 of 180 greedy on/off pairs had the same completion-text SHA-256. This is a hash comparison, not a semantic check, and no lossless claim is made.
- **Exploratory sample.** Four prompts, three repetitions each. The sample SD in the JSON mixes prompt and run variation and is not a confidence interval.
- **Sequential, unlocked.** Arms ran one after another without randomized order or locked GPU clocks. Small differences may depend on order, clocks or server implementation. GPU telemetry is in `evidence/telemetry.csv.gz`.
- **Short context only.** All prompts are short and context is 16,384. Drafter behavior at deep filled context was not measured.
- **Different builds.** The Unsloth and mainline builds differ in source and compiler. Their off arms (81.08 versus 59.83 tok/s at greedy 128) are not an isolated build-only comparison.
- **One card.** Results are for one RTX 3090 and are not a prediction for other GPUs.

## Files

| File | Contents |
|---|---|
| [results-summary.json](results-summary.json) | 28 cell means, sample SDs, per-prompt means, pooled acceptance, peak memory, same-build ratios |
| [results-per-run.json](results-per-run.json) / [results-per-run.csv](results-per-run.csv) | All 336 requests |
| [native-timings.jsonl](native-timings.jsonl) | Server timing, generation settings and stop fields for each request |
| [protocol.json](protocol.json) / [requests.json](requests.json) / [templates.json](templates.json) | Settings, request bodies, rendered prompts |
| [tasks/](tasks/) | The four prompt files |
| [commands.json](commands.json) | Server, build and download commands |
| [models.json](models.json) / [systems.json](systems.json) | GGUF hashes and hardware/build records |
| [build-comparison.json](build-comparison.json) | Separate `llama-bench` check |
| [validation.json](validation.json) | Cell completeness, fixed-length checks and greedy output-hash comparisons |
| [evidence/](evidence/) | 28 sanitized server logs and combined GPU telemetry, gzip-compressed |
| [manifest.json](manifest.json) / [SHA256SUMS](SHA256SUMS) | File inventory and hashes |
| [validate.py](validate.py) | Offline package check |

Generated completion and reasoning text is not published. Native timing excerpts keep the timing, settings and stop fields. Captured paths are normalized to `/study`.

## Verify

From this directory, without a model or network access:

```sh
python3 validate.py
shasum -a 256 -c SHA256SUMS
```

## Credits

DSpark drafter and GGUF quants: [Unsloth](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF). Runtime: [llama.cpp](https://github.com/ggml-org/llama.cpp) and the [Unsloth release](https://github.com/unslothai/llama.cpp/releases/tag/b12675-mix-d14fe45). Weights: Thinking Machines. MAJOR//minor designed the tests; AI agents ran them and assembled the evidence. Data: CC BY 4.0.
