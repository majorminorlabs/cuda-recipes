import argparse, csv, json, math, os, random, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
from .validate import ROOT
PRIVATE = Path(os.environ.get("NEMOTRON_PRIVATE_DIR", Path.home() / ".local/share/nemotron-compression"))

def pct(values, p):
    if not values: return None
    xs=sorted(values); x=(len(xs)-1)*p; lo=int(x); hi=min(lo+1,len(xs)-1)
    return xs[lo]+(xs[hi]-xs[lo])*(x-lo)

def bootstrap_means(task_values, seed=70015, n=10000):
    keys=list(task_values); rng=random.Random(seed); vals=[]
    for _ in range(n):
        sample=[task_values[rng.choice(keys)] for _ in keys]
        vals.append(sum(sample)/len(sample))
    return [pct(vals,.025),pct(vals,.975)]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--db",default=str(PRIVATE / "results/checkpoint.sqlite3")); ap.add_argument("--gpu-hours",type=float,default=None); args=ap.parse_args()
    db=sqlite3.connect(ROOT/args.db); db.row_factory=sqlite3.Row
    rows=[dict(r) for r in db.execute("SELECT * FROM trials WHERE status IN ('complete','failed') ORDER BY model,task_id,repetition")]; db.close()
    tasks={t["id"]:t for t in json.loads((ROOT/"benchmark/tasks.json").read_text())}
    schedule=json.loads((ROOT/"benchmark/schedule.json").read_text())
    expected={f"{r['model']}:{r['task_id']}:{r['repetition']}" for r in schedule["trials"]}
    observed={r["trial_id"] for r in rows}
    if observed!=expected: raise SystemExit(f"analysis requires exactly the 240 scheduled terminal observations; missing={len(expected-observed)} unexpected={len(observed-expected)}")
    by_model=defaultdict(list); by_category=defaultdict(list); by_task=defaultdict(list); by_model_time=defaultdict(float)
    for r in rows:
        by_model[r["model"]].append(r); by_category[(r["model"],tasks[r["task_id"]]["category"])].append(r); by_task[(r["model"],r["task_id"])].append(r); by_model_time[r["model"]]+=r["wall_s"] or 0
    model_avg={}; model_ci={}
    for model in ("nemotron","qwen"):
        avgs={task:sum(x["success"] for x in vals)/len(vals) for (m,task),vals in by_task.items() if m==model}
        model_avg[model]=sum(avgs.values())/len(avgs)
        model_ci[model]=bootstrap_means(avgs)
    differences={task:sum(r["success"] for r in by_task[("nemotron",task)])/3-sum(r["success"] for r in by_task[("qwen",task)])/3 for task in tasks}
    paired_ci=bootstrap_means(differences)
    summary={"n_scored_trials":len(rows),"trial_success":{"nemotron":sum(r["success"] for r in by_model["nemotron"])/len(by_model["nemotron"]),"qwen":sum(r["success"] for r in by_model["qwen"])/len(by_model["qwen"])},"mean_task_success":{"nemotron":model_avg["nemotron"],"qwen":model_avg["qwen"],"bootstrap_95_ci":{"nemotron":model_ci["nemotron"],"qwen":model_ci["qwen"]}},"paired_difference_nemotron_minus_qwen":sum(differences.values())/40,"paired_difference_bootstrap_95_ci":paired_ci,"pair_discordance":{},"categories":{},"task_comparisons":{},"performance":{},"failure_classifications":{},"gpu_hours":args.gpu_hours}
    for task in tasks:
        n=sum(r["success"] for r in by_task[("nemotron",task)])/3; q=sum(r["success"] for r in by_task[("qwen",task)])/3
        summary["task_comparisons"][task]={"nemotron_success_fraction":n,"qwen_success_fraction":q,"difference":n-q}
    n_only=sum(d>0 for d in differences.values()); q_only=sum(d<0 for d in differences.values())
    summary["pair_discordance"]={"nemotron_favored_tasks":n_only,"qwen_favored_tasks":q_only,"tied_tasks":40-n_only-q_only}
    for model in ("nemotron","qwen"):
        summary["categories"][model]={}
        for ci,cat in enumerate(("coding","terminal_system","tool_use","structured_data","multi_step")):
            x=by_category[(model,cat)]; ids=[t for t in tasks if tasks[t]["category"]==cat]
            means={t:sum(r["success"] for r in by_task[(model,t)])/3 for t in ids}
            summary["categories"][model][cat]={"successes":sum(r["success"] for r in x),"trials":len(x),"completed_generations":sum(r["status"]=="complete" for r in x),"success_rate":sum(r["success"] for r in x)/len(x),"task_cluster_bootstrap_95_ci":bootstrap_means(means,70015+ci)}
        rs=by_model[model]; times=[r["wall_s"] for r in rs if r["wall_s"] is not None]; p_tps=[r["prompt_tps"] for r in rs if r["prompt_tps"]]; d_tps=[r["decode_tps"] for r in rs if r["decode_tps"]]
        successes=sum(r["success"] for r in rs)
        summary["performance"][model]={"assigned_trials":len(rs),"latency_observations":len(times),"completed_generations":sum(r["status"]=="complete" for r in rs),"mean_completion_s":statistics.mean(times) if times else None,"median_completion_s":statistics.median(times) if times else None,"p95_completion_s":pct(times,.95),"prompt_tps_mean":statistics.mean(p_tps) if p_tps else None,"decode_tps_mean":statistics.mean(d_tps) if d_tps else None,"peak_vram_mib":max((r["peak_vram_mib"] for r in rs if r["peak_vram_mib"] is not None),default=None),"peak_ram_kib":max((r["peak_ram_kib"] for r in rs if r["peak_ram_kib"] is not None),default=None),"successful_trials_per_generation_gpu_hour":successes/(by_model_time[model]/3600) if by_model_time[model] else None,"successful_trials_per_paid_gpu_hour":successes/args.gpu_hours if args.gpu_hours else None}
        summary["failure_classifications"][model]={}
        for r in rs:
            if not r["success"]:
                k=r["failure_class"] or "incorrect_or_unclassified"; summary["failure_classifications"][model][k]=summary["failure_classifications"][model].get(k,0)+1
    out=ROOT/"results"; out.mkdir(exist_ok=True)
    (out/"canonical-results.json").write_text(json.dumps(summary,indent=2)+"\n")
    fields=[k for k in rows[0] if k not in ("raw_path","response")]
    with (out/"canonical-runs.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:v for k,v in r.items() if k in fields} for r in rows])
    with (out/"canonical-tasks.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["task_id","category","nemotron_success_fraction","qwen_success_fraction","difference"]);w.writeheader()
        for t,v in summary["task_comparisons"].items(): w.writerow({"task_id":t,"category":tasks[t]["category"],**v})
    (ROOT/"publication").mkdir(exist_ok=True)
    labels=[("coding","Coding"),("terminal_system","Terminal/system"),("tool_use","Tool use"),("structured_data","Structured data"),("multi_step","Multi-step")]
    bars=[]
    for i,(key,label) in enumerate(labels):
        y=70+i*54
        for model,color,offset in (("nemotron","#2878b5",0),("qwen","#df7b32",20)):
            value=summary["categories"][model][key]["success_rate"]
            bars.append(f'<text x="12" y="{y+14+offset}" font-size="12">{label if offset==0 else ""}</text><rect x="135" y="{y+offset}" width="{500*value:.1f}" height="15" fill="{color}"/><text x="{142+500*value:.1f}" y="{y+12+offset}" font-size="11">{value:.1%}</text>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="720" height="370" viewBox="0 0 720 370"><rect width="100%" height="100%" fill="white"/><text x="12" y="28" font-size="18" font-family="sans-serif">Task success by category</text>'+''.join(bars)+'<rect x="430" y="340" width="12" height="12" fill="#2878b5"/><text x="448" y="351" font-size="12">Nemotron</text><rect x="535" y="340" width="12" height="12" fill="#df7b32"/><text x="553" y="351" font-size="12">Qwen</text></svg>'
    (ROOT/"publication/category-success.svg").write_text(svg+'\n')
    performance=[]
    max_t=max((summary["performance"][m]["median_completion_s"] or 0 for m in ("nemotron","qwen")),default=1) or 1
    for i,(model,label,color) in enumerate((("nemotron","Nemotron","#2878b5"),("qwen","Qwen","#df7b32"))):
        y=90+i*78; value=summary["performance"][model]["median_completion_s"] or 0
        performance.append(f'<text x="18" y="{y+16}" font-size="13">{label}</text><rect x="130" y="{y}" width="{440*value/max_t:.1f}" height="22" fill="{color}"/><text x="{138+440*value/max_t:.1f}" y="{y+16}" font-size="12">{value:.1f}s median</text>')
    psvg='<svg xmlns="http://www.w3.org/2000/svg" width="720" height="270" viewBox="0 0 720 270"><rect width="100%" height="100%" fill="white"/><text x="18" y="34" font-size="18" font-family="sans-serif">Median agent completion time</text>'+''.join(performance)+'<text x="130" y="245" font-size="11">Per assigned trial; lower is faster</text></svg>'
    (ROOT/"publication/completion-time.svg").write_text(psvg+'\n')
    manifest=json.loads((ROOT/"models/manifest.json").read_text())
    def fmt(value, digits=1): return "n/a" if value is None else f"{value:.{digits}f}"
    def pc(value): return "n/a" if value is None else f"{value:.1%}"
    lines=["# Nemotron 74B 2-bit vs Qwen3.8 27B Q4_K_M", "", "## Findings", "",
        f"The benchmark contains {len(rows)} terminal trial records across 40 fixed tasks, with three scheduled repetitions per model and task. Overall assigned-trial success was {pc(summary['trial_success']['nemotron'])} for Nemotron and {pc(summary['trial_success']['qwen'])} for Qwen.", "",
        f"Mean task success was {pc(model_avg['nemotron'])} for Nemotron (95% task-cluster bootstrap CI {pc(model_ci['nemotron'][0])} to {pc(model_ci['nemotron'][1])}) and {pc(model_avg['qwen'])} for Qwen (95% task-cluster bootstrap CI {pc(model_ci['qwen'][0])} to {pc(model_ci['qwen'][1])}). The paired difference (Nemotron minus Qwen) was {pc(summary['paired_difference_nemotron_minus_qwen'])} (95% task-cluster bootstrap CI {pc(paired_ci[0])} to {pc(paired_ci[1])}).", "",
        f"Task-level direction: {n_only} tasks favored Nemotron, {q_only} favored Qwen, and {40-n_only-q_only} tied. These estimates describe only this frozen text-only task suite and these model/runtime configurations.", "",
        "![Task success by category](category-success.svg)", "", "## Category success", "", "| Category | Nemotron | Qwen |", "|---|---:|---:|"]
    for key,label in labels:
        n=summary["categories"]["nemotron"][key]; q=summary["categories"]["qwen"][key]
        lines.append(f"| {label} | {pc(n['success_rate'])} ({pc(n['task_cluster_bootstrap_95_ci'][0])}–{pc(n['task_cluster_bootstrap_95_ci'][1])}) | {pc(q['success_rate'])} ({pc(q['task_cluster_bootstrap_95_ci'][0])}–{pc(q['task_cluster_bootstrap_95_ci'][1])}) |")
    lines += ["", "Intervals are 95% task-cluster bootstrap intervals with 10,000 resamples and fixed seed 70015.", "", "## Task-level comparisons", "", "| Task | Category | Nemotron | Qwen | Difference |", "|---|---|---:|---:|---:|"]
    for task_id,value in summary["task_comparisons"].items():
        lines.append(f"| {task_id} | {tasks[task_id]['category']} | {pc(value['nemotron_success_fraction'])} | {pc(value['qwen_success_fraction'])} | {pc(value['difference'])} |")
    lines += ["", "## Inference performance and resource use", "", "![Median completion time](completion-time.svg)", "", "| Metric | Nemotron | Qwen |", "|---|---:|---:|"]
    metric_rows=[("Mean completion time (s)","mean_completion_s",1),("Median completion time (s)","median_completion_s",1),("95th percentile completion time (s)","p95_completion_s",1),("Prompt throughput (tokens/s)","prompt_tps_mean",1),("Decode throughput (tokens/s)","decode_tps_mean",1),("Peak VRAM (MiB)","peak_vram_mib",0),("Peak container RAM (GiB)","peak_ram_kib",1),("Successful trials per generation GPU-hour","successful_trials_per_generation_gpu_hour",1),("Successful trials per paid GPU-hour","successful_trials_per_paid_gpu_hour",1)]
    for label,key,digits in metric_rows:
        def val(model):
            value=summary["performance"][model][key]
            if key=="peak_ram_kib" and value is not None: value=value/(1024*1024)
            return fmt(value,digits)
        lines.append(f"| {label} | {val('nemotron')} | {val('qwen')} |")
    lines += ["", "Completion time is per assigned trial and includes all model/tool turns. Generation GPU-hours sum trial execution wall time; paid GPU-hours include provider uptime for the complete experiment.", "", "## Failures", ""]
    for model,label in (("nemotron","Nemotron"),("qwen","Qwen")):
        detail=", ".join(f"{kind}: {count}" for kind,count in sorted(summary["failure_classifications"][model].items())) or "none"
        lines.append(f"- **{label}:** {detail}")
    lines += ["", "## Deployment tradeoffs", "", "| Model | Checkpoint / quantization | Peak VRAM | Median trial time | Decode rate |", "|---|---|---:|---:|---:|"]
    for model,label in (("nemotron","Nemotron"),("qwen","Qwen")):
        perf=summary["performance"][model]; spec=manifest[model]
        lines.append(f"| {label} | {spec['quantization']} | {fmt(perf['peak_vram_mib'],0)} MiB | {fmt(perf['median_completion_s'])} s | {fmt(perf['decode_tps_mean'])} tok/s |")
    lines += ["", "Both models were run one at a time with the same 16,384-token context ceiling, llama.cpp build, no-offload requirement, KV cache type, and task runner. Nemotron's official checkpoint and Qwen's third-party GGUF conversion have different provenance; Qwen's Hub scanner metadata included an inconsistent warning, while its embedded chat template matched the pinned official upstream template exactly. The benchmark uses text tasks only and does not evaluate image or video input.", "", "## Failure interpretation and limits", "", "Tool calls execute against deterministic, isolated simulator state; terminal tasks score command/result contracts without granting unrestricted shell access. Success scores are binary and task-specific, with no language-model judge. Task-cluster intervals reflect the 40-task sample; they do not establish performance on the broader distribution of user workloads. Setup failures and interrupted assignments remain failures in the scheduled denominator and are classified separately.", "", f"Paid GPU time recorded for this run: {fmt(args.gpu_hours,2)} hours. Rental cost and full provenance are recorded in the local study notes; this public artifact contains no provider host identifiers or raw model traces.", ""]
    (ROOT/"publication/research-report.md").write_text("\n".join(lines))
    print(json.dumps({"trial_success":summary["trial_success"],"paired_difference":summary["paired_difference_nemotron_minus_qwen"],"bootstrap_ci":summary["paired_difference_bootstrap_95_ci"]},indent=2))

if __name__=="__main__":main()
