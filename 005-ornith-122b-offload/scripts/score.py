#!/usr/bin/env python3
"""Exact-match task check for CUDA Recipes 005 (Ornith-1.5-122B).

Hits a running llama-server, thinking off, temp 0. Stdlib only.
Records answers plus llama-server timings (decode speed, MTP draft stats) per task.

Usage:
  python3 score.py --label q4_ncmoe41 --url http://localhost:8080
  python3 score.py --label q4_mtp --url http://localhost:8081
"""
import argparse, json, re, time, urllib.request

SYSTEM = "Answer with only the final answer, nothing else."


def norm(s):
    s = (s or "").strip().strip("`").strip()
    s = re.sub(r"[.\s]+$", "", s)
    return s.lower()


def ask(url, prompt, max_tokens):
    body = json.dumps({
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0, "top_k": 1, "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    return data, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--tasks", default="tasks/tasks.jsonl")
    ap.add_argument("--label", required=True)
    ap.add_argument("--max-tokens", type=int, default=64)
    a = ap.parse_args()

    tasks = [json.loads(l) for l in open(a.tasks) if l.strip()]
    out_path = f"logs/tasks_{a.label}.jsonl"
    correct, tps = 0, []
    with open(out_path, "w") as out:
        for t in tasks:
            data, wall = ask(a.url, t["prompt"], a.max_tokens)
            got = data["choices"][0]["message"].get("content", "")
            ok = norm(got) == norm(t["answer"])
            correct += ok
            tim = data.get("timings", {})
            if tim.get("predicted_per_second"):
                tps.append(tim["predicted_per_second"])
            out.write(json.dumps({"id": t["id"], "ok": ok, "expected": t["answer"],
                                  "got": got, "wall_s": round(wall, 2), "timings": tim}) + "\n")
            print(f"{t['id']} {'PASS' if ok else 'FAIL'}  got={got!r}")
    med = sorted(tps)[len(tps) // 2] if tps else None
    summary = {"label": a.label, "correct": correct, "total": len(tasks),
               "median_decode_tok_s": med}
    print(json.dumps(summary))
    with open("logs/tasks_summary.jsonl", "a") as f:
        f.write(json.dumps(summary) + "\n")


if __name__ == "__main__":
    main()
