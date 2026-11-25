# Commands and settings

The original command records are archived with the run. Local machine paths, network endpoints, and credentials are omitted here; model and source paths are normalized to `/study`.

## Quality server

```sh
llama-server -m /study/models/Ternary-Bonsai-2.5-27B-PTQ1_0.gguf --host localhost --port 8000 --ctx-size 16384 --parallel 1 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja --verbose -np 1
```

The MTP quality server used the corresponding `-mtp.gguf` and the official CUDA defaults `--spec-type draft-mtp --spec-draft-n-min 0 --spec-draft-n-max 3 --spec-draft-p-min 0.1`. The suite runner supplied the frozen 001 prompts, seeds, sampling values, and turn limits.

## `llama-bench`

```sh
llama-bench -m /study/models/MODEL.gguf -r 3 -p 512 -n 128 -ngl 99 -t 8 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa auto -o json
llama-bench -m /study/models/MODEL.gguf -r 3 -p 0 -n 128 --no-warmup -d DEPTH -ngl 99 -t 8 -b BATCH -ub UBATCH -ctk KV -ctv KV -fa auto -o json
```

## Fixed-prompt MTP check

The server comparison served the MTP-head file on three fixed prompts, once without speculative options and once with `--spec-type draft-mtp --spec-draft-n-min 0 --spec-draft-n-max 3 --spec-draft-p-min 0.1`, always with `-np 1`. Exact counters and throughput are in `evidence/mtp-speed.json`.
