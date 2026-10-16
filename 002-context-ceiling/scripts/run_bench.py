#!/usr/bin/env python3
"""Run one llama-bench invocation and one VRAM sampler per configured depth."""
import argparse
import csv
import json
import subprocess
import sys
import re
import time
from pathlib import Path

from common import (BENCH_COLS, Budget, BudgetStop, Sampler, bench_rows_from_json,
                    config, csv_append, manifest, validate_bench_revision)

def configured_bench_flags(cfg, help_text):
    """Translate server flags supported by llama-bench, adapting flash-attn syntax."""
    match = re.search(r"(?:-fa\s*,\s*)?--flash-attn\s*<([^>]+)>", help_text, re.I)
    if not match:
        raise RuntimeError("llama-bench --help did not document the flash-attention option")
    accepted = {x.strip().lower() for x in re.split(r"[|/, ]+", match.group(1)) if x.strip()}
    flash = "on" if "on" in accepted else ("1" if "1" in accepted else None)
    if flash is None:
        raise RuntimeError(f"llama-bench flash-attention syntax is not recognized: {match.group(1)}")
    aliases = {"--batch-size": "-b", "--ubatch-size": "-ub", "--cache-type-k": "-ctk", "--cache-type-v": "-ctv", "-ngl": "-ngl", "--flash-attn": "-fa"}
    flags, items = [], [part for flag in cfg["fixed_server_flags"] for part in flag.split()]
    i = 0
    while i < len(items):
        key = items[i]
        if key in aliases:
            if i + 1 >= len(items): raise RuntimeError(f"missing value for configured flag {key}")
            value = items[i + 1]
            if key == "--flash-attn": value = flash
            flags.extend((aliases[key], value))
            i += 2
        else:
            # --parallel and --jinja are server-only and have no llama-bench counterpart.
            i += 2 if i + 1 < len(items) else 1
    return flags, flash

def main():
    cfg, mf = config(), manifest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--llama-bench", default="llama-bench")
    ap.add_argument("--nvidia-smi", default="nvidia-smi")
    ap.add_argument("--models", nargs="*", choices=cfg["models"], default=list(cfg["models"]))
    args = ap.parse_args()
    budget = Budget(cfg)
    try:
        help_result = subprocess.run([args.llama_bench, "--help"], capture_output=True, text=True, timeout=30)
        if help_result.returncode:
            raise RuntimeError(f"llama-bench --help exited with status {help_result.returncode}")
        fixed, flash_value = configured_bench_flags(cfg, help_result.stdout + help_result.stderr)
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        print(f"PREFLIGHT FAILED: {e}", file=sys.stderr)
        return 1
    print(f"llama-bench flash-attn syntax confirmed: -fa {flash_value}", flush=True)

    root = Path(args.model_dir)
    load_path = Path(__file__).resolve().parents[1] / "DATA" / "load-results.csv"
    with load_path.open(newline="") as f:
        loads = list(csv.DictReader(f))
    bench_path = Path(__file__).resolve().parents[1] / "DATA" / "bench-results.csv"
    with bench_path.open(newline="") as f:
        previous_bench = list(csv.DictReader(f))
    ceilings = {}
    for model in args.models:
        marked = [r for r in loads if r["model"] == model and r["is_ceiling"] == "1" and r["loaded_full_gpu"] == "1"]
        if len(marked) != 1:
            print(f"{model}: expected exactly one completed full-GPU ceiling row", file=sys.stderr)
            return 1
        ceilings[model] = int(marked[0]["ctx_size"])

    bench_cfg = cfg["bench"]
    overhead = int(bench_cfg["prompt_tokens"]) + int(bench_cfg["generated_tokens"])
    completed = {}
    for row in previous_bench:
        key = (row["model"], int(row["depth_tokens"]), row["depth_label"])
        completed[key] = completed.get(key, 0) + 1
    fixed_by_model, deep_by_model = {}, {}
    for model in args.models:
        ceiling = ceilings[model]
        tasks = []
        for depth in bench_cfg["depths_tokens"]:
            depth = int(depth)
            if depth + overhead <= ceiling:
                tasks.append((depth, "fixed", bench_cfg["repetitions"]["depth_0" if depth == 0 else "depth_gt_0"]))
            else:
                print(f"SKIP {model} fixed depth {depth}: depth + {overhead} exceeds ceiling {ceiling}")
        fixed_by_model[model] = tasks
        deep = round(0.9 * ceiling)
        deep_by_model[model] = (deep, "ceiling90", bench_cfg["repetitions"]["depth_gt_0"]) if deep + overhead <= ceiling else None

    def run_task(model, depth, label, repetitions, can_skip=False):
        key = (model, depth, label)
        existing_rows = completed.get(key, 0)
        if existing_rows == repetitions:
            print(f"REUSE {model} {label} depth={depth}: complete rows already saved")
            return "complete"
        if existing_rows:
            raise RuntimeError(f"incomplete existing rows for {model} {label} depth={depth}: {existing_rows}/{repetitions}")
        model_path = root / Path(mf[model]["files"][0]["path"]).name
        if not model_path.is_file(): raise RuntimeError(f"missing model file for {model}")
        detail = {"depth": depth, "model": model, "label": label}
        guess = budget.estimate_seconds("bench", detail)
        if can_skip:
            try:
                remaining = budget.ensure_can_start("bench", detail, projected_seconds=guess)
            except BudgetStop as e:
                print(f"SKIP {model} ceiling90 depth {depth}: projected runtime crosses hard stop ({e})")
                return "skipped"
        else:
            remaining = budget.remaining_seconds
            if remaining <= 0:
                raise BudgetStop("configured hard stop reached before the next fixed depth")
        cmd = [args.llama_bench, "-m", str(model_path), *fixed, "-p", str(bench_cfg["prompt_tokens"]), "-n", str(bench_cfg["generated_tokens"]), "-d", str(depth), "-r", str(repetitions), "-o", "json"]
        print(f"bench {model} {label} depth={depth} repetitions={repetitions}", flush=True)
        sampler = Sampler(args.nvidia_smi)
        started = time.monotonic()
        sampler.start()
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=remaining)
        except subprocess.TimeoutExpired:
            print("BUDGET STOP: hard stop reached during llama-bench; current depth was not written", file=sys.stderr)
            return "stopped"
        finally:
            sampler.stop()
        duration = time.monotonic() - started
        if not sampler.values: raise RuntimeError("nvidia-smi produced no VRAM samples; refusing to write incomplete bench rows")
        if proc.returncode: raise RuntimeError(f"llama-bench failed for {model} at depth {depth}: {proc.stderr[-1000:]}")
        try:
            validate_bench_revision(proc.stdout, cfg)
        except (ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(str(e)) from e
        rows = bench_rows_from_json(proc.stdout, cfg, model, depth, label, sampler.peak_mib)
        if len(rows) != repetitions: raise RuntimeError(f"expected {repetitions} rows, parser produced {len(rows)}")
        csv_append("bench-results.csv", BENCH_COLS, rows)
        completed[key] = repetitions
        budget.record("bench", duration, {"depth": depth, "model": model, "label": label})
        return "complete"

    stopped = False
    try:
        for model in args.models:
            for depth, label, repetitions in fixed_by_model[model]:
                if run_task(model, depth, label, repetitions) == "stopped":
                    stopped = True; break
            if stopped: break
        if not stopped:
            # Ceiling90 tasks are kept last and run only when their projected duration fits.
            for model in args.models:
                task = deep_by_model[model]
                if task is None:
                    print(f"SKIP {model} ceiling90: depth + {overhead} exceeds ceiling {ceilings[model]}")
                    continue
                status = run_task(model, *task, can_skip=True)
                if status == "stopped": stopped = True; break
                if status == "skipped" and budget.remaining_seconds <= 0:
                    stopped = True
                    break
    except BudgetStop as e:
        print(f"BUDGET STOP: {e}", file=sys.stderr)
        stopped = True
    except RuntimeError as e:
        print(f"RUN STOPPED: {e}", file=sys.stderr)
        return 1
    print(budget.report(), flush=True)
    if stopped: print("Stopped at the configured hard limit; completed depth rows were saved.", flush=True)
    return 0

if __name__ == "__main__": sys.exit(main())
