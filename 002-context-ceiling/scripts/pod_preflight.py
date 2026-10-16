#!/usr/bin/env python3
"""Check pinned llama-bench flash-attention syntax and capture 16K log diagnostics."""
import argparse
import subprocess
import sys
from pathlib import Path

from common import Budget, BudgetStop, config
from run_bench import configured_bench_flags

def main():
    cfg = config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--llama-source", required=True, help="Source checkout used to build the pinned executables")
    ap.add_argument("--llama-bench", default="llama-bench")
    ap.add_argument("--llama-server", default="llama-server")
    ap.add_argument("--nvidia-smi", default="nvidia-smi")
    ap.add_argument("--models", nargs="*", choices=cfg["models"], default=list(cfg["models"]))
    args = ap.parse_args()
    budget = Budget(cfg)
    try:
        revision = subprocess.run(["git", "-C", args.llama_source, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=15)
        if revision.returncode or revision.stdout.strip() != cfg["llama_cpp_revision"]:
            raise RuntimeError("llama.cpp source checkout does not match the configured revision")
        dirty = subprocess.run(["git", "-C", args.llama_source, "diff", "--quiet", "HEAD", "--"], timeout=15)
        if dirty.returncode:
            raise RuntimeError("llama.cpp source checkout has tracked changes")
        remaining = budget.ensure_can_start("bench_help", projected_seconds=5)
        help_output = subprocess.run([args.llama_bench, "--help"], capture_output=True, text=True,
                                     timeout=min(30, remaining))
        if help_output.returncode:
            raise RuntimeError(f"llama-bench --help exited with status {help_output.returncode}")
        _flags, flash = configured_bench_flags(cfg, help_output.stdout + help_output.stderr)
    except (OSError, subprocess.SubprocessError, RuntimeError, BudgetStop) as e:
        print(f"PREFLIGHT FAILED: llama-bench --help did not confirm flash-attention syntax: {e}", file=sys.stderr)
        return 1
    print(f"PASS: pinned llama-bench help accepts -fa {flash}.")
    print("Next, each 16K anchor load checks the live layer-placement and model/KV/compute/CPU_Mapped log strings against the parser; RS is parsed and summed when present.")
    script = Path(__file__).with_name("run_load_sweep.py")
    for model in args.models:
        command = [sys.executable, str(script), "--model-dir", args.model_dir,
                   "--llama-server", args.llama_server, "--nvidia-smi", args.nvidia_smi,
                   "--models", model, "--preflight-only"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.stdout: print(result.stdout, end="")
        if result.stderr: print(result.stderr, end="", file=sys.stderr)
        if result.returncode or "PREFLIGHT PASS:" not in result.stdout:
            print(f"PREFLIGHT FAILED for {model}; stop before the full sweep.", file=sys.stderr)
            return result.returncode or 1
    print("Preflight complete; anchor load rows are saved and the full sweep will reuse them.")
    print(budget.report())
    return 0

if __name__ == "__main__": sys.exit(main())
