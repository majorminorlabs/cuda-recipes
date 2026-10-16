#!/usr/bin/env python3
"""Load sweep and bounded ceiling search using /health and llama.cpp diagnostics."""
import argparse
import csv
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import (Budget, BudgetStop, INTERNAL, LOAD_COLS, Sampler, cli_flags,
                    config, csv_rewrite, manifest, parse_load_log, audit_lines)

def probe_health(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

def wait_for_health(port, proc, timeout, probe=probe_health, sleep=time.sleep):
    """Wait for HTTP 200; HTTP 503 and connection errors mean the server is still loading."""
    end = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < end:
        if proc.poll() is not None:
            return False, f"server exited before readiness (exit {proc.returncode})"
        last_status = probe(port)
        if last_status == 200:
            return True, ""
        sleep(min(0.4, max(0.0, end - time.monotonic())))
    return False, f"readiness timeout after {timeout:.0f}s (last HTTP status {last_status})"

def save_audit(model, ctx, log):
    folder = INTERNAL / "load-logs"
    folder.mkdir(parents=True, exist_ok=True)
    previous = folder.glob(f"{model}-ctx-{ctx}-attempt-*.txt")
    attempt = max((int(p.stem.rsplit("-", 1)[1]) for p in previous), default=0) + 1
    path = folder / f"{model}-ctx-{ctx}-attempt-{attempt:02d}.txt"
    path.write_text(audit_lines(log))

def attempt(binary, model_path, ctx, model, cfg, nvidia_smi, budget):
    allowed = budget.remaining_seconds
    if allowed <= 0:
        raise BudgetStop("configured hard stop reached before the next load attempt")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cmd = [binary, "--model", str(model_path), "--ctx-size", str(ctx), *cli_flags(cfg), "--port", str(port), "--verbose"]
    sampler = Sampler(nvidia_smi)
    started = time.monotonic()
    # llama.cpp diagnostics can include non-UTF-8 bytes; preserve the stream
    # with replacement characters so the reader thread keeps draining stdout.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    sampler.start()
    line_queue = queue.Queue()
    def read_output():
        for line in proc.stdout:
            line_queue.put(line)
        line_queue.put(None)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    health_timeout = min(900.0, allowed)
    budget_interrupted = False
    ready, reason = False, ""
    try:
        ready, reason = wait_for_health(port, proc, health_timeout)
        if budget.remaining_seconds <= 0:
            budget_interrupted = True
    finally:
        if proc.poll() is None:
            if budget.remaining_seconds <= 0:
                proc.kill()
                proc.wait()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=min(15, budget.remaining_seconds))
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        sampler.stop()
        reader.join()
    lines = []
    while True:
        try: item = line_queue.get_nowait()
        except queue.Empty: break
        if item is None: continue
        lines.append(item)
    log = "".join(lines)
    save_audit(model, ctx, log)
    if budget_interrupted:
        raise BudgetStop("0.9 GPU-hour hard stop reached while waiting for model readiness")
    elapsed = time.monotonic() - started
    budget.record("load", elapsed, {"model": model, "ctx": int(ctx)})
    if not sampler.values:
        raise RuntimeError("nvidia-smi produced no VRAM samples; refusing to write an incomplete load row")
    parsed = parse_load_log(log)
    if ctx == int(cfg["ctx_sizes"][0]) and ready:
        required = ("layers_total", "model_buffer_mib", "kv_buffer_mib", "compute_buffer_mib", "cpu_mapped_mib")
        absent = [name for name in required if parsed[name] in ("", 0)]
        if re.search(r"CUDA\d+ RS buffer size", log, re.I) and parsed["rs_buffer_mib"] == "":
            absent.append("rs_buffer_mib")
        if absent:
            raise RuntimeError(f"pod preflight could not match required load diagnostics ({', '.join(absent)}); inspect the private audit file")
    loaded = ready and parsed["layers_total"] > 0 and parsed["layers_on_cuda"] == parsed["layers_total"]
    error = "" if loaded else reason
    if ready and not loaded:
        error = "not every layer placed on CUDA"
    return {"model": model, "ctx_size": int(ctx), "loaded_full_gpu": int(loaded), **parsed,
            "peak_vram_load_mib": sampler.peak_mib, "is_ceiling": 0, "error": error}

def main():
    cfg, mf = config(), manifest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--llama-server", default="llama-server")
    ap.add_argument("--nvidia-smi", default="nvidia-smi")
    ap.add_argument("--models", nargs="*", choices=cfg["models"], default=list(cfg["models"]))
    ap.add_argument("--preflight-only", action="store_true", help="Load and parse only the 16K anchor; the full sweep reuses this row")
    args = ap.parse_args()
    budget = Budget(cfg)
    root = Path(args.model_dir)
    step = int(cfg["ceiling_search"]["step"])
    data_path = Path(__file__).resolve().parents[1] / "DATA" / "load-results.csv"
    with data_path.open(newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    for row in all_rows:
        for key in ("ctx_size", "loaded_full_gpu", "layers_on_cuda", "layers_total", "is_ceiling"):
            row[key] = int(row[key])
        for key in ("model_buffer_mib", "kv_buffer_mib", "rs_buffer_mib", "compute_buffer_mib", "cpu_mapped_mib", "peak_vram_load_mib"):
            if row[key] == "": row[key] = ""
    hard_stop = False
    for model in args.models:
        model_path = root / Path(mf[model]["files"][0]["path"]).name
        if not model_path.is_file(): ap.error(f"missing model file for {model}")
        native = int(cfg["native_ctx_max"][model])
        grid = [int(x) for x in cfg["ctx_sizes"] if int(x) <= native]
        if grid != sorted(grid): ap.error("ctx_sizes must be ascending")
        model_rows = [r for r in all_rows if r["model"] == model]
        seen = {int(r["ctx_size"]): r for r in model_rows}
        def run(ctx):
            if ctx in seen:
                return seen[ctx]
            print(f"load {model} ctx={ctx}", flush=True)
            row = attempt(args.llama_server, model_path, ctx, model, cfg, args.nvidia_smi, budget)
            model_rows.append(row)
            all_rows.append(row)
            seen[ctx] = row
            return row
        try:
            if args.preflight_only:
                anchor = int(cfg["ctx_sizes"][0])
                row = run(anchor)
                csv_rewrite("load-results.csv", LOAD_COLS, all_rows)
                if row["loaded_full_gpu"]:
                    print(f"PREFLIGHT PASS: {model} anchor load is full-GPU; parsed diagnostics saved privately.")
                else:
                    print(f"PREFLIGHT LOAD FAILED: {model} anchor: {row['error']}", file=sys.stderr)
                continue
        except BudgetStop as e:
            print(f"BUDGET STOP: {e}", file=sys.stderr)
            break
        failed_at = None
        highest_passed = 0
        ceiling_known = False
        try:
            for ctx in grid:
                row = run(ctx)
                if not row["loaded_full_gpu"]:
                    failed_at = ctx
                    break
                highest_passed = ctx
            if failed_at is None:
                # Native maximum loaded: the spec defines it as the ceiling; do not probe above.
                if grid and grid[-1] == native:
                    ceiling = seen[native]
                    ceiling["is_ceiling"] = 1
                    ceiling_known = True
                else:
                    failed_at = None
            if failed_at is not None:
                low = highest_passed // step
                high = failed_at // step
                while high - low > 1:
                    mid = (low + high) // 2
                    row = run(mid * step)
                    if row["loaded_full_gpu"]:
                        low = mid
                    else:
                        high = mid
                successes = [r for r in model_rows if r["loaded_full_gpu"]]
                if successes:
                    max(successes, key=lambda r: int(r["ctx_size"]))["is_ceiling"] = 1
                    ceiling_known = True
        except BudgetStop as e:
            print(f"BUDGET STOP: {e}", file=sys.stderr)
            hard_stop = True
        finally:
            if ceiling_known:
                ceiling = max((r for r in model_rows if r["loaded_full_gpu"]), key=lambda r: int(r["ctx_size"]))
                for row in model_rows: row["is_ceiling"] = 0
                ceiling["is_ceiling"] = 1
            if model_rows:
                csv_rewrite("load-results.csv", LOAD_COLS, all_rows)
        if hard_stop:
            break
    print(budget.report(), flush=True)
    if hard_stop:
        print("Stopped at the configured hard stop; completed load rows were saved.", flush=True)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except BudgetStop as e:
        print(f"BUDGET STOP: {e}", file=sys.stderr)
        sys.exit(0)
