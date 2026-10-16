# Limitations and interpretation

- **Strict task contracts:** outcomes are binary task-specific contracts. A semantically plausible answer can fail if it violates a restricted AST, exact command, JSON, or tool-action sequence rule. This measures benchmark compliance, not general intelligence.
- **Small fixed sample:** 40 tasks and three repetitions per model/task/GPU. Task-cluster intervals are wide and paired overall/model intervals include zero. Results may not generalize to user workloads.
- **Outcome variance:** 33 of 240 paired assignments differed. Equal seeds do not ensure identical token sequences across architecture, driver, and GPU execution paths. The GPUs were tested on separate provider nodes, batches were not interleaved, and there were no repeated hardware-condition sessions.
- **Confounding:** GPU model, CUDA target, driver, and provider node differ. The observed success-rate gap cannot be attributed to hardware. Speed differences are observed under this runtime setup, not universal GPU benchmarks.
- **Models are not a quantization-only comparison:** model family, training, architecture, artifact conversion/provenance, and quantization differ. No causal effect of bit width is isolated.
- **Latency and throughput differ:** decode tokens/s is a generation rate; full-trial latency includes prompt processing, generation and tool cycles. Neither alone describes interactive quality. Batch order was fixed by model to avoid reloading large weights, so order/thermal effects are not ruled out.
- **Memory measures:** peak VRAM is reported from run telemetry; system RAM is container peak. File-backed `CPU_Mapped` GGUF buffers do not mean CPU layer offloading.
- **Cost:** GPU rental totals are rate-times-provider-uptime estimates. Corrected RTX 5090 posted invoice detail was unavailable at final verification. They exclude any unreported non-GPU charges.
- **Tool use:** deterministic simulator tools and task-specific strict action contracts do not represent unrestricted real-world tool use.
