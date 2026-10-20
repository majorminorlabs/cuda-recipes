#!/usr/bin/env python3
"""Validate negative controls, task references, and focused regression tests."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command, cwd, env=None):
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout[-6000:]


def clear_bytecode(root):
    for path in root.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-cache", type=Path, required=True)
    ap.add_argument("--python", default="python3")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "validation.json")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    base = Path(__file__).parent
    catalog = json.loads((base / "tasks.json").read_text())
    results = []
    for task in catalog["tasks"]:
        cache = args.repo_cache / task["repo"]
        if not cache.exists():
            # Folder names differ for the attrs repository.
            cache = args.repo_cache / {"attrs":"attrs"}.get(task["repo"], task["repo"])
        work = Path(tempfile.mkdtemp(prefix="lh-" + task["id"].lower() + "-"))
        try:
            repo = args.repo_cache / {"more-itertools":"more-itertools", "requests":"requests", "packaging":"packaging", "click":"click", "attrs":"attrs"}[task["repo"]]
            rev = task["repository"]["revision"]
            archive = subprocess.Popen(["git", "archive", rev], cwd=repo, stdout=subprocess.PIPE)
            untar = subprocess.run(["tar", "-x", "-C", str(work)], stdin=archive.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            archive.stdout.close()
            if archive.wait() or untar.returncode:
                raise RuntimeError("git archive failed")
            case = base / "cases" / task["id"]
            starter = (case / "starter.patch").read_text()
            if starter:
                patch = subprocess.run(["git", "apply", "--check", "-"], cwd=work, input=starter, text=True, capture_output=True)
                if patch.returncode:
                    raise RuntimeError("starter patch check: " + patch.stderr)
                subprocess.run(["git", "apply", "-"], cwd=work, input=starter, text=True, check=True)
            test_path = case / "challenge_test.py"
            py_path = str(work if task["repo"] == "more-itertools" else work / "src")
            env = dict(os.environ, PYTHONPATH=py_path + os.pathsep + os.environ.get("PYTHONPATH", ""), PYTHONDONTWRITEBYTECODE="1")
            cmd = [args.python, "-m", "pytest", "-q", str(test_path)]
            clear_bytecode(work)
            negative_rc, negative_output = run(cmd, work, env)
            if negative_rc == 0:
                raise RuntimeError("negative control incorrectly passed challenge tests")
            reference = (case / "reference.patch").read_text()
            patch = subprocess.run(["git", "apply", "--check", "-"], cwd=work, input=reference, text=True, capture_output=True)
            if patch.returncode:
                raise RuntimeError("reference patch check: " + patch.stderr)
            subprocess.run(["git", "apply", "-"], cwd=work, input=reference, text=True, check=True)
            clear_bytecode(work)
            positive_rc, positive_output = run(cmd, work, env)
            if positive_rc:
                raise RuntimeError("reference failed challenge tests:\n" + positive_output)
            upstream_rc, upstream_output = run([args.python, "-m", "pytest", "-q", task["test_file"], "-k", task["required_test_name"]], work, env)
            if upstream_rc:
                raise RuntimeError("reference failed repository regression test:\n" + upstream_output)
            upstream_target, selector = task["upstream_targeted_tests"].split(" -k ", 1)
            upstream_rc, upstream_output = run([args.python,"-m","pytest","-q",upstream_target,"-k",selector],work,env)
            if upstream_rc:
                raise RuntimeError("reference failed pre-existing targeted repository tests:\n" + upstream_output)
            # Publish validation status only. Pytest output includes private local
            # paths and environment details that are not part of the public artifact.
            results.append({"task_id":task["id"],"negative_control":"failed as expected",
                            "reference":"passed challenge, task-authored, and existing targeted repository tests"})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        print(task["id"], "PASS")
    payload = {"suite":"long_horizon_v1","tasks":len(results),"positive_references_passed":len(results),"negative_controls_rejected":len(results),"results":results}
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k:payload[k] for k in ("tasks","positive_references_passed","negative_controls_rejected")}))


if __name__ == "__main__":
    main()
