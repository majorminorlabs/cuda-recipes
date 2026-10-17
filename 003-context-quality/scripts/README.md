# Phase 0 and Phase 1 scripts

`generate_phase0.py` deterministically rebuilds Moby-Dick haystacks and 180 randomized questions from the checked-in `DATA/study-config.json` rules, records insertion offsets and token counts for all three pinned tokenizers, and freezes SHA-256 values in `DATA/documents/manifest.json`. It uses the public-domain source copy staged under ignored `_internal/`.

`score.py` extracts a bare, fenced, or last top-level JSON object and performs deterministic exact match after case/whitespace normalization; `multi_retrieval` uses set equality. Its self-test confirms references are supported by the document, negative controls fail, and every answer value is absent from its question and token/digit-disjoint from its entity key. `score_responses.py` rebuilds answer rows offline from saved raw response JSONL.

`show_examples.py` prints two `long_64k` examples per task, with exact planted sentences and nearby prose, to inspect before Phase 1.

`pod_preflight.py` is for the configured RTX 3090 pod only. It verifies the downloaded Qwen3.6 GGUF locally by byte size and SHA-256, builds pinned llama.cpp for CUDA architecture 86, records sanitized host/build details, health-gates the server, and measures Qwen3.6 decoding with an approximately 8K prompt. The completed sanitized record is in `DATA/host-build-manifest.json`.

`arm_preflight.py` runs three control questions per model with thinking off and saves preflight responses. All models must pass before `run_phase1.py` will start. `run_phase1.py` is for the configured RTX 3090 host only. Run in this order while preserving `_internal/phase1-clock.json`:

```sh
python3 scripts/run_phase1.py --model qwen36_35b_a3b --model-file "$MODEL_QWEN36" --pod-created-epoch "$POD_CREATED_EPOCH"
python3 scripts/run_phase1.py --model nemotron --model-file "$MODEL_NEMOTRON" --no-reset-clock
python3 scripts/run_phase1.py --model qwen38_27b --model-file "$MODEL_QWEN38" --no-reset-clock
```

The first-model invocation writes the mandatory budget checkpoint only after all its questions finish. Later models are refused unless that checkpoint says `CONTINUE`. The checkpoint projects the total from measured first-model output length, capped at 256 tokens, 002 measured speed by prompt depth, and elapsed run time. It stops before the next model if the projection exceeds the 1.2 GPU-hour hard stop. The runner tries 131,072 context first, then descends in 8,192-token steps until `/health` returns HTTP 200 and every layer is on CUDA. It records allocation buffers from the real, nonzero model-allocation pass, matching CUDA Recipes 002. Every inference response is appended to `_internal/responses/primary-<model>.jsonl`. The document is the first chat message and the question is last; subsequent answer rows record cached prompt tokens from the response.

Run the CPU-only mock checks with `python3 scripts/dry_run.py`. They cover parser/scorer controls, raw-response-aware scratch validation, automatic budget checkpoint writes, and the empty primary arm remaining PENDING. `python3 -m unittest discover -s tests -v` runs JSON extraction tests. Phase 0b performs no GPU execution.
