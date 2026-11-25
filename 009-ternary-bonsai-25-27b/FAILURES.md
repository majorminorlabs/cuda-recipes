# Failures and changed attempts

- Two PrismML source build attempts failed while loading the optional bundled UI assets. Both full outputs are retained with the run. Disabling UI explicitly using `LLAMA_BUILD_UI=OFF` and `LLAMA_USE_PREBUILT_UI=OFF` completed the pinned source build.
- Seventeen initial benchmark attempts failed before model loading because the runner expected per-model directories while the files were in a flat directory. The runner paths were corrected; the successful rows are reported, and original failures remain archived.
- The Qwen 262144 filled-context Q8_0 attempt failed CUDA allocation: a 149.62 MiB allocation and subsequent 156,893,184-byte buffer allocation failed, followed by context creation failure. No Qwen result is reported at that depth.
- An early model metadata pin for Q2_0 had a malformed checksum and was rejected before loading. The verified model manifest checksum was used for the completed Q2_0 benchmark.
- A local Hugging Face model copy was interrupted after partial transfer. That incomplete local cache is retained in the run archive and was not used for any measurements.
- Pod-to-Mac data transfer included an interrupted initial attempt; no files were deleted. The final complete transfer and integrity checks are recorded in the private run record.

The larger-depth Bonsai profiles were run with the listed reduced batch/ubatch settings directly. They are not presented as retries after documented default-profile failures.
