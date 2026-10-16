#!/usr/bin/env python3
"""Verify both pinned GGUF payload hashes. Reads all expected hashes from config."""
import argparse, hashlib, sys
import time
from pathlib import Path
from common import Budget, config, manifest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True, help="Directory containing the two manifest-named GGUF files")
    ap.add_argument("--reset-budget-window", action="store_true", help="Start a fresh hard-stop clock for a newly started pod")
    args = ap.parse_args()
    cfg, mf, root = config(), manifest(), Path(args.model_dir)
    budget = Budget(cfg)
    if args.reset_budget_window:
        budget.reset()
    started = time.monotonic()
    ok = True
    for name, entry in cfg["models"].items():
        files = mf[name]["files"]
        for f in files:
            path = root / Path(f["path"]).name
            if not path.is_file():
                print(f"FAIL {name}: expected GGUF file is missing")
                ok = False
                continue
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""): h.update(block)
            digest = h.hexdigest()
            expected = entry["artifact_sha256"]
            print(f"{'PASS' if digest == expected else 'FAIL'} {name}: sha256 {'matches' if digest == expected else 'does not match'} config")
            ok &= digest == expected
    budget.record("verify", time.monotonic() - started)
    print(budget.report())
    return 0 if ok else 1

if __name__ == "__main__": sys.exit(main())
