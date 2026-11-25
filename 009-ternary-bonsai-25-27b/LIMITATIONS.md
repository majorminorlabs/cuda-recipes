# Limitations

- The study has one RTX 3090 system. Results do not establish performance across cards or systems.
- The Qwen quality baseline is reused from study 001. Its task-suite server used the older llama.cpp commit recorded there; Bonsai used the pinned PrismML fork. The quality flags, tasks, seeds, and scorer are frozen from 001, but runtime builds differ.
- The MTP on/off server comparison used three fixed prompts. It is a narrow throughput check, not a quality result or a repeatable workload distribution.
- `llama-bench` does not expose the MTP speculative-decoding controls. The PTQ1 MTP-head file's benchmark row had drafting disabled; it is not an MTP-on speed result.
- Filled-context rows use synthetic prompts and different KV/batch settings at larger depths. F16 KV was used through 128K for Bonsai; Q8 KV was used at 262K. Do not compare these rows as if settings were identical.
- The Qwen 262144 filled-context attempt failed allocation. No successful Qwen result exists at that depth.
- Results depend on the pinned models, software builds, driver, CUDA versions, and documented settings. Timing variation is expected.
