# Limitations

- **Fit + speed only.** No long-context quality, retrieval, or answer-accuracy evaluation was run.
- **Synthetic fill.** llama-bench generated the filled context; real documents and prompts may have different performance.
- **Single-run deeper points.** Depth zero had three repetitions; every depth above zero had one run, so deeper-point variability is unknown.
- **One GPU host.** Results are from one RunPod Secure Cloud RTX 3090 24GB. Other cards, drivers, hosts, and thermal conditions may differ.
- **Driver differs from 001.** This run used driver 610.57.04; 001 used 580.126.20. Also, 002 speed used llama-bench, while 001 used its task harness. Those speed measurements are not equivalent.
- **Fixed cache configuration.** Q8_0 K/V cache and server settings were held fixed; other cache formats may change fit and speed.
- **Two model artifacts.** Findings apply only to the pinned GGUF files, not to all quantizations or model versions.
- **Anchor attempt excluded.** The first 16K Nemotron anchor attempt crashed in runner log decoding. The runner was fixed and the retry succeeded; this was not a model failure.
- **Cost is an estimate.** 0.867 GPU-hour multiplied by the advertised $0.50/hour RTX 3090 rate gives about $0.43; it is not a provider invoice.
