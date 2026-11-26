# Reproduction

Build llama.cpp commit `a866b4ade63921826c530307a368fbca3a334a0b` with CUDA enabled. Set `BASE_GGUF`, `LORA_GGUF` and `LLAMA_SERVER` to your downloaded model files and built server executable.

```sh
"$LLAMA_SERVER" --model "$BASE_GGUF" --lora "$LORA_GGUF" \
  --lora-init-without-apply --n-gpu-layers 99 --ctx-size 16384 \
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --parallel 1 \
  --chat-template-kwargs '{"enable_thinking":true}' \
  --host 127.0.0.1 --port 8080 --alias qwen3.8-study
```

In a separate terminal from the suite directory:

```sh
python3 -m src.run_v2 --api http://127.0.0.1:8080/v1 --model both \
  --schedule schedule-paired.json --db results/trials.sqlite3 --raw-dir results/raw
```

The pinned server emitted a deprecation notice for CLI template kwargs. Every request also explicitly enables thinking. Keep one server slot; the runner toggles global adapter state before each trial. Tasks and seeds are frozen. Tool actions run in the suite simulator.
