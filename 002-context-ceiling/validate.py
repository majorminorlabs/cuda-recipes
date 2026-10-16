#!/usr/bin/env python3
"""Dependency-free checks for CUDA Recipes 002. Run from this folder: python3 validate.py"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOAD_COLS = ["model", "ctx_size", "loaded_full_gpu", "layers_on_cuda", "layers_total", "model_buffer_mib", "kv_buffer_mib",
             "rs_buffer_mib", "compute_buffer_mib", "cpu_mapped_mib", "peak_vram_load_mib", "is_ceiling", "error"]
BENCH_COLS = ["model", "depth_tokens", "depth_label", "repetition", "prompt_tps", "decode_tps", "peak_vram_mib"]
VRAM_MIB = 24576

def rows(name, cols):
    with (ROOT / "DATA" / name).open(newline="") as f:
        r = csv.DictReader(f)
        assert r.fieldnames == cols, f"{name}: header mismatch {r.fieldnames}"
        return list(r)

def reps_for(cfg, depth):
    r = cfg["bench"]["repetitions"]
    return r["depth_0"] if depth == 0 else r["depth_gt_0"]

def main():
    cfg = json.loads((ROOT / "DATA" / "study-config.json").read_text())
    load, bench = rows("load-results.csv", LOAD_COLS), rows("bench-results.csv", BENCH_COLS)
    if not load and not bench:
        print("PENDING: schema and config OK, no results yet."); return 0
    errors, b = [], cfg["bench"]
    overhead = b["prompt_tokens"] + b["generated_tokens"]
    for m in cfg["models"]:
        native = cfg["native_ctx_max"][m]
        ml = [r for r in load if r["model"] == m]
        if not ml: errors.append(f"{m}: no load rows"); continue
        if any(int(r["ctx_size"]) > native for r in ml): errors.append(f"{m}: load attempt above native max {native}")
        ok = sorted(int(r["ctx_size"]) for r in ml if r["loaded_full_gpu"] == "1")
        bad = sorted(int(r["ctx_size"]) for r in ml if r["loaded_full_gpu"] == "0")
        if ok and bad and min(bad) < ok[-1]: errors.append(f"{m}: non-monotonic loads (fail at {min(bad)} below pass at {ok[-1]})")
        ceil = [r for r in ml if r["is_ceiling"] == "1"]
        if len(ceil) != 1: errors.append(f"{m}: expected exactly one ceiling row, got {len(ceil)}"); continue
        c = int(ceil[0]["ctx_size"])
        if c != ok[-1]: errors.append(f"{m}: ceiling is not the largest full-GPU load")
        if c < native and (c + cfg["ceiling_search"]["step"]) not in bad: errors.append(f"{m}: ceiling {c} not bracketed by a failure at {c + cfg['ceiling_search']['step']}")
        for r in ml:
            if r["loaded_full_gpu"] == "1" and r["layers_on_cuda"] != r["layers_total"]:
                errors.append(f"{m} ctx {r['ctx_size']}: marked full-GPU but layers {r['layers_on_cuda']}/{r['layers_total']}")
            if r["peak_vram_load_mib"] and float(r["peak_vram_load_mib"]) > VRAM_MIB:
                errors.append(f"{m} ctx {r['ctx_size']}: peak VRAM above card capacity")
        mb = [x for x in bench if x["model"] == m]
        for d in b["depths_tokens"]:
            n = sum(1 for x in mb if int(x["depth_tokens"]) == d and x["depth_label"] == "fixed")
            if d + overhead > c:
                if n: errors.append(f"{m} depth {d}: benched past ceiling {c}")
            elif n != reps_for(cfg, d): errors.append(f"{m} depth {d}: {n}/{reps_for(cfg, d)} rows")
        extra = [x for x in mb if x["depth_label"] == "ceiling90"]
        if extra and any(int(x["depth_tokens"]) != round(0.9 * c) for x in extra): errors.append(f"{m}: ceiling90 depth != round(0.9 × {c})")
    if errors:
        print("FAIL:"); [print("  -", e) for e in errors]; return 1
    print(f"PASS: {len(load)} load rows, {len(bench)} bench rows, one bracketed ceiling per model, complete depth/repetition grid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
