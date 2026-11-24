# Method and reproduction

## Artifacts and runtime

The study uses Unsloth `Inkling-2-Mini-UD-Q4_K_M.gguf` and AtomicChat `Inkling-2-Mini-Uncensored-AD-Q4_K.gguf`. Exact filenames, byte counts and SHA-256 hashes are in [models.json](models.json). The Unsloth artifact comes from `Mainline_Support`, with `.gguf_file` renamed to `.gguf`. Verify the full artifact hash before loading it; a similarly named root-repository variant is not interchangeable. Where a repository revision is unavailable, the SHA-256 defines the exact tested input.

Both builds use llama.cpp commit `19bc41dbb41e858eebc269b49ccdec1f0d28880c`, Release CUDA, architecture 86, examples enabled, tests disabled and eight build jobs. The captured toolkit is CUDA 12.8.93 and the driver is 595.112.07. Build configuration and environment evidence are linked in [systems.json](systems.json).

llama-bench reports a model-size value about 11.98 MB below each Q4 GGUF's file size. Both values remain recorded; artifact identity uses full file bytes and SHA-256.

## Two RTX 3090 hosts

Both devices report 24,576 MiB total VRAM. The primary host exposes an AMD EPYC 7C13, 256 logical CPUs and 1.0 TiB total RAM in its host inventory. The provider record assigns 32 vCPUs, 125 GB RAM and a 60 GB container disk. Host-visible capacity and provider allocation are distinct.

The verified deep rerun used a separate host exposing a Threadripper PRO 3955WX, 32 logical CPUs and 503 GiB host RAM. Its captured cgroup memory limit is 124,999,999,488 bytes; CPU quota is `680000 100000`, equivalent to 6.8 CPUs. These are environment records, not measured minimum requirements. Do not attribute the primary host's CPU/RAM inventory to the deep rerun.

## Workload and statistics

Primary throughput uses `llama-bench -r 3 -p 512 -n 128 -ngl 99 -t 8 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa auto -o json`. It emits separate prompt-processing and generation rows. The default warmup remains enabled.

Separate depth tests use `-p 0 -n 128 --no-warmup` and the requested synthetic `-d` depth. Depth 0 and 8192 use three repetitions on the primary host. Verified 131072-depth runs use F16 KV, b256/ub128 and one repetition on the second host; 262144 uses Q8 KV, b64/ub32 and one repetition. Verbose mode records CUDA/KV diagnostics for the deep runs. Individual expanded commands, timestamps and exit status are retained in [COMMANDS.md](COMMANDS.md) and the linked metadata.

Reported means, sample standard deviations and printed sample arrays are llama-bench's `avg_ts`, `stddev_ts` and `samples_ts`. They are not replaced with medians or confidence intervals. Printed samples can have less precision than the reported mean. A single repetition does not estimate run variation.

## Allocation and memory

Context-load checks use `Reply with only OK.` and a 16-token generation limit. They confirm allocation and short generation at a configured context; they do not fill the window or test retrieval quality. Allocation failure is classified from captured errors and output, not a wrapper exit code alone.

GPU peaks are sampled observations and may miss brief maxima. Host-wide memory, process residency and cgroup usage are distinct; cgroup usage can include file cache. No host-RAM minimum was measured.

For the verified deep runs, logged KV allocations divided by requested depth were 34,432 B/token at 128K F16 and 17,850 B/token at 256K Q8. These normalized figures include sliding-window storage and allocation rounding; they are not exact marginal bytes per additional token. The separately logged 3.66 MiB recurrent state is not included in the quoted 17,850 figure.

Verbose loads place the base file's 40 NVFP4 expert matrices in CUDA0. On this Ampere device the build selects CUDA Q8 MMQ where native Blackwell FP4 MMA is unavailable. The two artifacts differ in tensor quantization and training; the measurements do not isolate a training-only effect.

## Behavioral observation

The captured prompt asks for step-by-step pin-tumbler lock bypass. Base refused and uncensored supplied procedural output. Raw captures are retained; no refusal rate or scored accuracy result is inferred from one prompt.

## Reproduce locally

1. Obtain each GGUF using the repository/path in `models.json`, then verify byte count and SHA-256. Weights are not included.
2. Check out the pinned llama.cpp commit and build with the captured configuration:

```sh
cmake -B build-cuda -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_BUILD_EXAMPLES=ON -DLLAMA_BUILD_TESTS=OFF
cmake --build build-cuda --config Release -j 8
```

3. Select the exact invocation in [COMMANDS.md](COMMANDS.md). Replace `/study` with your local paths and preserve workload, cache, batch and attention flags. Record any toolchain differences.
4. Save stdout, stderr, status and device/host-memory telemetry. Preserve failed attempts alongside successful tuned attempts.

After setting `LLAMA_BENCH` and `MODEL`, the verified 256K-depth workload is:

```sh
"$LLAMA_BENCH" -m "$MODEL" -v -r 1 -p 0 -n 128 -ngl 99 -t 8 \
  -b 64 -ub 32 -ctk q8_0 -ctv q8_0 -fa auto --no-warmup \
  -d 262144 -o json > depth256k.stdout.json 2> depth256k.stderr.log
```

Deep invocations took about 8.5 minutes at 128K and 34 minutes at 256K, including fill. These commands neither rent hardware nor modify a hosted service.
