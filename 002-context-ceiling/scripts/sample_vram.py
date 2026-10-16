#!/usr/bin/env python3
"""Standalone GPU memory sampler. Reads minimum sampling rate from study-config.json."""
import argparse, subprocess, sys, time
from common import Budget, config

def main():
    cfg = config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=min(0.4, 1 / cfg["vram_sampling_hz_min"]))
    ap.add_argument("--nvidia-smi", default="nvidia-smi")
    args = ap.parse_args()
    budget = Budget(cfg)
    if args.interval > min(0.4, 1 / cfg["vram_sampling_hz_min"]):
        ap.error("interval violates the configured minimum sampling frequency")
    try:
        deadline = time.monotonic()
        while True:
            if budget.remaining_seconds <= 0:
                print("BUDGET STOP: configured hard limit reached")
                print(budget.report())
                return 0
            print(subprocess.check_output([args.nvidia_smi, "--query-gpu=timestamp,memory.used", "--format=csv,noheader,nounits"], text=True, timeout=budget.remaining_seconds).strip(), flush=True)
            deadline += args.interval
            time.sleep(min(max(0.0, deadline - time.monotonic()), budget.remaining_seconds))
    except KeyboardInterrupt:
        return 0
    except subprocess.TimeoutExpired:
        print("BUDGET STOP: hard stop reached during nvidia-smi sampling")
        print(budget.report())
        return 0
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"nvidia-smi sampling failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__": sys.exit(main())
