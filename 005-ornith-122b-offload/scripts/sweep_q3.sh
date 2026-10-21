#!/usr/bin/env bash
set -u
cd /workspace/005
M3=$(find /workspace/models/UD-Q3_K_XL -maxdepth 1 -name '*.gguf' | sort | head -1)
: > logs/sweep_ncmoe_q3_oom.txt
for nc in 49 44 40 36 32; do
  label="sweep_ncmoe_q3_${nc}"
  rm -f "logs/${label}.exit_code"
  bash scripts/run_bench.sh "$label" -m "$M3" -ngl 99 -fa on -lm none -t 16 -ncmoe "$nc" -p 2048 -n 128 -r 3
  rc=$?
  printf 'ncmoe=%s exit=%s\n' "$nc" "$rc" >> logs/sweep_ncmoe_q3_status.txt
  if [ "$rc" -ne 0 ]; then
    printf 'ncmoe=%s failed; see %s.stderr\n' "$nc" "$label" >> logs/sweep_ncmoe_q3_oom.txt
  fi
done
