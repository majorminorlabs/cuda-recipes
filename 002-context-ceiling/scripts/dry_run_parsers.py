#!/usr/bin/env python3
"""Exercise load, health and llama-bench parsers against samples in a scratch copy."""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import (BENCH_COLS, LOAD_COLS, bench_rows_from_json, config,
                    audit_lines, health_status_sequence, parse_load_log, validate_bench_revision)
from run_load_sweep import wait_for_health
from run_bench import configured_bench_flags

SAMPLE_LOAD = """llama_model_load: offloaded 66/66 layers to GPU
llama_model_load: CUDA0 model buffer size = 0.00 MiB
llama_kv_cache: CUDA0 KV buffer size = 0.00 MiB
llama_kv_cache: CUDA0 RS buffer size = 32.00 MiB
llama_context: CUDA0 compute buffer size = 384.00 MiB
llama_model_load: offloaded 66/66 layers to GPU
llama_model_load: CPU_Mapped model buffer size = 682.03 MiB
llama_model_load: CUDA0 model buffer size = 15088.32 MiB
llama_kv_cache: CUDA0 KV buffer size = 512.00 MiB
llama_kv_cache: CUDA0 KV buffer size = 1.25 MiB
llama_kv_cache: CUDA0 RS buffer size = 16.00 MiB
llama_kv_cache: CUDA0 RS buffer size = 0.75 MiB
llama_context: CUDA0 compute buffer size = 192.00 MiB
llama_context: CUDA0 compute buffer size = 16.00 MiB
"""

class LiveProcess:
    def poll(self): return None

def write_csv(path, columns, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def main():
    cfg = config()
    parsed = parse_load_log(SAMPLE_LOAD)
    expected = {"layers_on_cuda": 66, "layers_total": 66, "model_buffer_mib": 15088.32,
                "kv_buffer_mib": 513.25, "rs_buffer_mib": 16.75,
                "compute_buffer_mib": 208.0, "cpu_mapped_mib": 682.03}
    assert parsed == expected, f"load parser mismatch: {parsed}"
    audited = audit_lines(SAMPLE_LOAD)
    assert audited.count("CUDA0 KV buffer size") == 3 and audited.count("CUDA0 RS buffer size") == 3
    assert parse_load_log(SAMPLE_LOAD.replace("llama_kv_cache: CUDA0 RS buffer size = 16.00 MiB\n", "").replace("llama_kv_cache: CUDA0 RS buffer size = 0.75 MiB\n", ""))["rs_buffer_mib"] == ""

    statuses = iter((503, 503, 200))
    ready, reason = wait_for_health(24001, LiveProcess(), 2, probe=lambda _port: next(statuses), sleep=lambda _n: None)
    assert ready and not reason and health_status_sequence((503, 503, 200)) == 200

    fake_help = "  -fa, --flash-attn <on|off|auto> (default: auto)"
    flags, flash = configured_bench_flags(cfg, fake_help)
    assert flash == "on" and flags[flags.index("-fa") + 1] == "on"
    flags_one, flash_one = configured_bench_flags(cfg, "  -fa, --flash-attn <0|1>")
    assert flash_one == "1" and flags_one[flags_one.index("-fa") + 1] == "1"

    load_rows, bench_rows = [], []
    for model in cfg["models"]:
        native = cfg["native_ctx_max"][model]
        ceiling = 131072
        load_rows.append({"model": model, "ctx_size": ceiling, "loaded_full_gpu": 1, **parsed,
                          "peak_vram_load_mib": 19000, "is_ceiling": 1, "error": ""})
        load_rows.append({"model": model, "ctx_size": ceiling + cfg["ceiling_search"]["step"],
                          "loaded_full_gpu": 0, "layers_on_cuda": 0, "layers_total": parsed["layers_total"],
                          "model_buffer_mib": parsed["model_buffer_mib"], "kv_buffer_mib": "",
                          "rs_buffer_mib": "", "compute_buffer_mib": "", "cpu_mapped_mib": parsed["cpu_mapped_mib"],
                          "peak_vram_load_mib": 19000, "is_ceiling": 0, "error": "sample allocation failure"})
        depths = [(int(d), "fixed") for d in cfg["bench"]["depths_tokens"]]
        depths.append((round(0.9 * ceiling), "ceiling90"))
        for depth, label in depths:
            if depth + cfg["bench"]["prompt_tokens"] + cfg["bench"]["generated_tokens"] > ceiling:
                continue
            repetitions = cfg["bench"]["repetitions"]["depth_0" if depth == 0 else "depth_gt_0"]
            samples = [float(100 + i) for i in range(repetitions)]
            decodes = [float(20 + i) for i in range(repetitions)]
            records = [{"n_prompt": cfg["bench"]["prompt_tokens"], "n_gen": 0, "n_depth": depth,
                        "avg_ts": sum(samples) / repetitions, "samples_ts": samples,
                        "build_commit": cfg["llama_cpp_revision"][:8]},
                       {"n_prompt": 0, "n_gen": cfg["bench"]["generated_tokens"], "n_depth": depth,
                        "avg_ts": sum(decodes) / repetitions, "samples_ts": decodes,
                        "build_commit": cfg["llama_cpp_revision"][:8]}]
            payload = json.dumps(records)
            validate_bench_revision(payload, cfg)
            bench_rows.extend(bench_rows_from_json(payload, cfg, model, depth, label, 20000))

    with tempfile.TemporaryDirectory(prefix="cuda-recipes-002-dry-run-") as temp:
        scratch = Path(temp)
        (scratch / "DATA").mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / "validate.py", scratch / "validate.py")
        shutil.copy2(Path(__file__).resolve().parents[1] / "DATA" / "study-config.json", scratch / "DATA" / "study-config.json")
        write_csv(scratch / "DATA" / "load-results.csv", LOAD_COLS, load_rows)
        write_csv(scratch / "DATA" / "bench-results.csv", BENCH_COLS, bench_rows)
        checked = subprocess.run([sys.executable, str(scratch / "validate.py")], capture_output=True, text=True)
        print(checked.stdout, end="")
        if checked.returncode:
            print(checked.stderr, file=sys.stderr)
            return checked.returncode
    print("Parser dry run PASS: two-pass allocation uses only real pass and sums its buffers; 503→503→200 readiness works; schema validates; real CSVs untouched.")
    return 0

if __name__ == "__main__": sys.exit(main())
