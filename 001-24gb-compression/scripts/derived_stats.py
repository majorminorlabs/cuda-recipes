"""Derived statistics used in the article that are not pre-computed in the data bundle.
Everything reads DATA. Run from repo root:
   python3 001-24gb-compression/scripts/derived_stats.py"""
import csv, json, random, statistics as st, collections, pathlib
_here = pathlib.Path(__file__).resolve()
D = _here.parents[1] / "DATA"
rows = list(csv.DictReader(open(D / "paired-runs.csv")))
cat = {t["id"]: t["category"] for t in json.load(open(D / "tasks.json"))}
mm = json.load(open(D / "model-manifest.json"))

print("== Tokens generated per trial (mean / median) and decode ratio")
for g in ("rtx3090", "rtx5090"):
    t = {}
    for m in ("nemotron", "qwen"):
        v = [r for r in rows if r["gpu"] == g and r["model"] == m]
        ct = [int(r["completion_tokens"]) for r in v]
        t[m] = (st.mean(ct), st.mean(float(r["decode_tps"]) for r in v))
        print(f"  {g} {m}: mean {st.mean(ct):.0f}  median {st.median(ct)}  decode {t[m][1]:.1f} tok/s")
    print(f"  {g} Nemotron/Qwen decode ratio {t['nemotron'][1]/t['qwen'][1]:.2f}, token ratio {t['nemotron'][0]/t['qwen'][0]:.2f}")
for m in ("nemotron", "qwen"):
    a = st.mean(float(r["decode_tps"]) for r in rows if r["gpu"] == "rtx3090" and r["model"] == m)
    b = st.mean(float(r["decode_tps"]) for r in rows if r["gpu"] == "rtx5090" and r["model"] == m)
    print(f"  {m} 5090/3090 decode ratio {b/a:.2f}")

print("== Failure classes pooled across GPUs")
fc = collections.Counter((r["model"], r["failure_class"]) for r in rows if r["success"] == "0")
for k, v in sorted(fc.items()): print("  ", k, v)
print("== Truncation by category (pooled)")
tc = collections.Counter((r["model"], cat[r["task_id"]]) for r in rows if r["failure_class"] == "truncated")
for k, v in sorted(tc.items()): print("  ", k, v)
print("== Tool-use success pooled")
for m in ("nemotron", "qwen"):
    v = [r for r in rows if r["model"] == m and cat[r["task_id"]] == "tool_use"]
    print(f"  {m}: {sum(int(r['success']) for r in v)}/{len(v)}")

print("== Tasks no model passed on either GPU")
by = collections.defaultdict(int)
for r in rows: by[r["task_id"]] += int(r["success"])
print("  ", [t for t in sorted(by) if by[t] == 0])

print("== Approx bits per weight (file bytes * 8 / nominal params)")
for m, p in (("nemotron", 74e9), ("qwen", 27e9)):
    b = mm[m]["files"][0]["bytes"]; print(f"  {m}: {b/1e9:.2f} GB ({b/2**30:.2f} GiB), ~{b*8/p:.2f} bpw")

print("== Execution order (from canonical run timestamps)")
for g in ("rtx3090", "rtx5090"):
    r = sorted(csv.DictReader(open(D / f"{g}-canonical-runs.csv")), key=lambda x: x["started_at"])
    blocks = [r[0]["model"]]
    for x in r[1:]:
        if x["model"] != blocks[-1]: blocks.append(x["model"])
    print(f"  {g}: {' -> '.join(blocks)}  ({r[0]['started_at']} to {r[-1]['ended_at']})")

print("== Paired task-cluster bootstrap, Qwen minus Nemotron (10,000 resamples, seed 20261015)")
tcmp = list(csv.DictReader(open(D / "task-comparisons.csv")))
d = collections.defaultdict(dict)
for x in tcmp: d[x["task_id"]][x["model"]] = (int(x["rtx3090_successes"]), int(x["rtx5090_successes"]))
T = sorted(d)
def diff(ts, gi):
    q = sum(sum(d[t]["qwen"][g] for g in gi) for t in ts); n = sum(sum(d[t]["nemotron"][g] for g in gi) for t in ts)
    return (q - n) / (len(ts) * 3 * len(gi))
random.seed(20261015)
for name, gi in (("rtx3090", [0]), ("rtx5090", [1]), ("pooled", [0, 1])):
    obs = diff(T, gi); bs = sorted(diff([random.choice(T) for _ in T], gi) for _ in range(10000))
    qw = sum(1 for t in T if sum(d[t]["qwen"][g] for g in gi) > sum(d[t]["nemotron"][g] for g in gi))
    nw = sum(1 for t in T if sum(d[t]["qwen"][g] for g in gi) < sum(d[t]["nemotron"][g] for g in gi))
    print(f"  {name}: {obs*100:+.2f} pp, 95% CI [{bs[249]*100:+.2f}, {bs[9749]*100:+.2f}]; tasks favoring Qwen {qw}, Nemotron {nw}, tied {40-qw-nw}")

print("== Single-turn vs tool-calling task groups (512-token per-turn cap applies only to tool-calling)")
groups = {"single-turn (coding, terminal, structured)": {"coding", "terminal_system", "structured_data"},
          "tool-calling (tool use, multi-step)": {"tool_use", "multi_step"}}
for gname, cs in groups.items():
    for g in ("rtx3090", "rtx5090", None):
        for m in ("nemotron", "qwen"):
            v = [r for r in rows if r["model"] == m and cat[r["task_id"]] in cs and (g is None or r["gpu"] == g)]
            s = sum(int(r["success"]) for r in v)
            print(f"  {gname} {g or 'pooled'} {m}: {s}/{len(v)} ({s/len(v)*100:.1f}%)")
