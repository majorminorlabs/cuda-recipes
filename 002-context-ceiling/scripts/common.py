#!/usr/bin/env python3
"""Shared config, parser, budget and telemetry helpers for CUDA Recipes 002."""
import csv
import json
import re
import statistics
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = ROOT / "_internal"
LOAD_COLS = ["model", "ctx_size", "loaded_full_gpu", "layers_on_cuda", "layers_total", "model_buffer_mib", "kv_buffer_mib", "rs_buffer_mib", "compute_buffer_mib", "cpu_mapped_mib", "peak_vram_load_mib", "is_ceiling", "error"]
BENCH_COLS = ["model", "depth_tokens", "depth_label", "repetition", "prompt_tps", "decode_tps", "peak_vram_mib"]

def config():
    return json.loads((ROOT / "DATA" / "study-config.json").read_text())

def manifest():
    return json.loads((ROOT / "DATA" / "model-manifest.json").read_text())

def csv_append(name, columns, rows):
    path = ROOT / "DATA" / name
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        writer.writerows(rows)

def csv_rewrite(name, columns, rows):
    path = ROOT / "DATA" / name
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)

def audit_lines(log):
    """Return only the raw buffer and layer-placement diagnostics for private audit."""
    pat = re.compile(r"(?:offloaded\s+\d+\s*/\s*\d+\s+layers?\s+to GPU|layers?\s+offloaded\s+to\s+GPU|CUDA\d+\s+(?:model|KV|RS|compute) buffer size|CPU_Mapped model buffer size)", re.I)
    return "".join(line for line in log.splitlines(keepends=True) if pat.search(line))

def parse_load_log(log):
    """Parse llama.cpp startup diagnostics, summing all matching buffer lines."""
    # llama.cpp emits a dry-run fit pass followed by real allocations. Start at
    # the first non-zero CUDA model buffer and parse only that allocation pass.
    model_lines = list(re.finditer(r"CUDA\d+ model buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)", log, re.I))
    real_start = next((m.start() for m in model_lines if float(m.group(1).replace(",", "")) > 0), None)
    if real_start is not None:
        placements = list(re.finditer(r"offloaded\s+\d+\s*/\s*\d+\s+layers?\s+to GPU|layers?\s+offloaded\s+to\s+GPU\s*=\s*\d+\s*/\s*\d+", log, re.I))
        prior = [m for m in placements if m.start() < real_start]
        block_start = prior[-1].start() if prior else real_start
        real_log = log[block_start:]
    else:
        real_log = ""
    layer_matches = re.findall(r"offloaded\s+(\d+)\s*/\s*(\d+)\s+layers?\s+to GPU", real_log, re.I)
    if not layer_matches:
        layer_matches = re.findall(r"layers?\s+offloaded\s+to\s+GPU\s*=\s*(\d+)\s*/\s*(\d+)", real_log, re.I)
    layers = tuple(map(int, layer_matches[-1])) if layer_matches else (0, 0)

    def total(pattern):
        matches = re.findall(pattern, real_log, re.I | re.M)
        if not matches:
            return ""
        values = []
        for raw_value, unit in matches:
            value = float(raw_value.replace(",", ""))
            values.append(value if unit.lower().startswith("mi") else value / (1024 * 1024))
        return round(sum(values), 2)

    return {
        "layers_on_cuda": layers[0], "layers_total": layers[1],
        "model_buffer_mib": total(r"CUDA\d+ model buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)"),
        "kv_buffer_mib": total(r"CUDA\d+ KV buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)"),
        "rs_buffer_mib": total(r"CUDA\d+ RS buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)"),
        "compute_buffer_mib": total(r"CUDA\d+ compute buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)"),
        "cpu_mapped_mib": total(r"CPU_Mapped model buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)"),
    }

def health_status_sequence(statuses):
    """Dry-run helper: health is ready only on HTTP 200, while 503 is still loading."""
    return next((status for status in statuses if status == 200), None)

class BudgetStop(Exception):
    pass

class Budget:
    """Shared wall-clock budget state for scripts run as separate commands on one pod."""
    def __init__(self, cfg=None):
        self.cfg = cfg or config()
        self.path = INTERNAL / "phase0-budget.json"
        INTERNAL.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"started_at_epoch": time.time(), "commands": []}
            self._save()

    def reset(self):
        self.state = {"started_at_epoch": time.time(), "commands": []}
        self._save()

    def _save(self):
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    @property
    def elapsed_seconds(self):
        return max(0.0, time.time() - float(self.state["started_at_epoch"]))

    @property
    def hard_stop_seconds(self):
        return float(self.cfg["budget_hard_stop_gpu_hours"]) * 3600

    @property
    def remaining_seconds(self):
        return max(0.0, self.hard_stop_seconds - self.elapsed_seconds)

    def estimate_seconds(self, kind, detail=None):
        history = [x for x in self.state["commands"] if x["kind"] == kind]
        if kind == "bench" and detail is not None:
            prior = [x for x in history if x.get("depth") is not None]
            if int(detail["depth"]) == 0 and not prior:
                return 45.0
            prior_nonzero = [x for x in prior if int(x["depth"]) > 0]
            if int(detail["depth"]) > 0 and not prior_nonzero:
                return 90.0 + int(detail["depth"]) / 2048.0
            if int(detail["depth"]) > 0:
                prior = prior_nonzero
            if prior:
                nearest = min(prior, key=lambda x: abs(int(x["depth"]) - int(detail["depth"])))
                old_depth = int(nearest["depth"])
                ratio = (int(detail["depth"]) + 640) / (old_depth + 640)
                return max(20.0, float(nearest["seconds"]) * ratio)
            return 120.0 * (int(detail["depth"]) + 640) / 640
        if history:
            return max(30.0, statistics.median(float(x["seconds"]) for x in history))
        return 120.0

    def ensure_can_start(self, kind, detail=None, projected_seconds=None):
        guess = projected_seconds if projected_seconds is not None else self.estimate_seconds(kind, detail)
        if self.remaining_seconds <= 0 or guess >= self.remaining_seconds:
            raise BudgetStop(f"hard stop reached/projected ({self.elapsed_seconds / 3600:.3f} GPU-h elapsed; projected {guess:.0f}s)")
        return self.remaining_seconds

    def record(self, kind, seconds, detail=None):
        item = {"kind": kind, "seconds": round(float(seconds), 3)}
        if detail:
            item.update(detail)
        self.state["commands"].append(item)
        self._save()

    def report(self):
        return f"budget elapsed {self.elapsed_seconds / 3600:.3f}/{self.cfg['budget_hard_stop_gpu_hours']} GPU-h hard stop"

class Sampler:
    """Samples VRAM at a 0.4-second cadence (2.5 Hz target)."""
    def __init__(self, nvidia_smi="nvidia-smi"):
        self.nvidia_smi = nvidia_smi
        min_interval = 1 / float(config()["vram_sampling_hz_min"])
        self.interval = min(0.4, min_interval)
        self.values = []
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        def loop():
            deadline = time.monotonic()
            while not self.stop_event.is_set():
                try:
                    out = subprocess.check_output([self.nvidia_smi, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True, stderr=subprocess.DEVNULL, timeout=self.interval)
                    vals = [int(x.strip()) for x in out.splitlines() if x.strip()]
                    if vals: self.values.append(max(vals))
                except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
                    pass
                deadline += self.interval
                self.stop_event.wait(max(0.0, deadline - time.monotonic()))
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread: self.thread.join()

    @property
    def peak_mib(self):
        return max(self.values) if self.values else ""

def cli_flags(cfg):
    return [part for flag in cfg["fixed_server_flags"] for part in flag.split()]

def bench_rows_from_json(payload, cfg, model, depth, label, peak):
    """Convert llama-bench JSON individual samples to the exact bench schema."""
    results = json.loads(payload)
    prompt = int(cfg["bench"]["prompt_tokens"])
    generated = int(cfg["bench"]["generated_tokens"])
    pp = next((r for r in results if int(r["n_prompt"]) == prompt and int(r["n_gen"]) == 0 and int(r["n_depth"]) == depth), None)
    tg = next((r for r in results if int(r["n_gen"]) == generated and int(r["n_prompt"]) == 0 and int(r["n_depth"]) == depth), None)
    if not pp or not tg: raise ValueError("missing prompt or generation result for configured depth")
    pps, tgs = pp.get("samples_ts", [pp["avg_ts"]]), tg.get("samples_ts", [tg["avg_ts"]])
    repetitions = cfg["bench"]["repetitions"]["depth_0" if depth == 0 else "depth_gt_0"]
    if len(pps) != repetitions or len(tgs) != repetitions:
        raise ValueError(f"expected {repetitions} raw samples; got {len(pps)} prompt and {len(tgs)} decode")
    return [{"model": model, "depth_tokens": depth, "depth_label": label, "repetition": i + 1,
             "prompt_tps": pps[i], "decode_tps": tgs[i], "peak_vram_mib": peak} for i in range(repetitions)]

def validate_bench_revision(payload, cfg):
    results = json.loads(payload)
    expected = str(cfg["llama_cpp_revision"]).lower()
    commits = {str(row.get("build_commit", "")).lower() for row in results}
    if not commits or "" in commits or any(not (expected.startswith(commit) or commit.startswith(expected)) for commit in commits):
        raise ValueError("llama-bench JSON build_commit does not match the configured llama.cpp revision")
    return results
