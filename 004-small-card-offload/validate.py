#!/usr/bin/env python3
"""Validate CUDA Recipes 004 result files against DATA/SCHEMA.md."""
import csv,json,os,sys
D="DATA";CORE={24,16,12};LOAD_CTX={32768,131072,262144};DEPTHS_128={0,32768,65536,117964};DEPTHS_32={0,16384,29491};REPS={1,2,3};MARGIN=500;errors=[]
def err(s): errors.append(s)
def load(name,required=True):
 p=os.path.join(D,name)
 if not os.path.exists(p):
  if required:err(f"missing {p}")
  return None
 with open(p,newline="") as f:return list(csv.DictReader(f))
def i(v):return int(float(v))

hp=os.path.join(D,"hosts.json")
if os.path.exists(hp):
 h=json.load(open(hp))
 required_hosts=("0","A","B")
 if os.path.exists(os.path.join(D,"bench-results.csv")):
  with open(os.path.join(D,"bench-results.csv"),newline="") as f:
   if any(r.get("host")=="C" for r in csv.DictReader(f)):required_hosts+=("C",)
 for label in required_hosts:
  host=h.get("hosts",{}).get(label)
  if not host:err(f"hosts.json missing host {label}");continue
  for k in ["cpu_model","llama_cpp_commit","model_sha256","wikitext_sha256"]:
   if not host.get(k):err(f"hosts.json host {label} missing {k}")
  for k in ["nproc","cpu_quota_vcpus","numa_nodes"]:
   if not host.get(k):err(f"hosts.json host {label} missing {k}")
else:err("missing DATA/hosts.json")

cal=load("calibration.csv");chosen={}
if cal is not None:
 for r in cal:
  if r.get("host")!="0":err("calibration: rows must be host 0")
 budgets={i(r["budget_gb"]) for r in cal}
 for b in CORE-budgets:err(f"calibration: no rows for {b}GB")
 if 8 not in budgets:err("calibration: no rows for 8GB")
 for b in budgets:
  rows=[r for r in cal if i(r["budget_gb"])==b];c=[r for r in rows if r["chosen"]=="1"]
  if b==8 and not c:continue
  if len(c)!=1:err(f"calibration: {b}GB has {len(c)} chosen rows (need 1)");continue
  r=c[0];ctx=i(r["ctx"])
  if ctx not in (32768,131072):err(f"calibration: unsupported chosen ctx {ctx} for {b}GB")
  if r["loaded"]!="1":err(f"calibration: {b}GB chosen N did not load")
  elif i(r["peak_vram_mib"])>b*1024-MARGIN:err(f"calibration: {b}GB chosen peak exceeds margin")
  if b==24 and i(r["n_cpu_moe"])!=0:err("calibration: 24GB baseline must use n_cpu_moe=0")
  chosen[b]=r
 for b,r in chosen.items():
  tried=sorted({i(x["n_cpu_moe"]) for x in cal if i(x["budget_gb"])==b and i(x["ctx"])==i(r["ctx"])})
  if len(tried)>10:err(f"calibration: {b}GB tried too many N values ({len(tried)}; expected binary search)")

lr=load("load-results.csv");loads_by={}
if lr is not None:
 for b,r in chosen.items():
  for c in LOAD_CTX:
   if not any(i(x["budget_gb"])==b and i(x["ctx"])==c for x in lr):err(f"load-results: missing {b}GB @ {c}")
 for r in lr:
  if r.get("host") not in ("0","C"):err("load-results: host must be 0 or C")
  b=i(r["budget_gb"]);ctx=i(r["ctx"]);loads_by[(r.get("host"),b,ctx)]=r
  if b in chosen and i(r["n_cpu_moe"])!=i(chosen[b]["n_cpu_moe"]):err(f"load-results: {b}GB uses N inconsistent with calibration")
  if r["loaded"]=="1" and i(r["peak_vram_mib"])>b*1024-MARGIN:err(f"load-results: {b}GB @ {ctx} exceeds budget margin")
  if r["loaded"]=="0" and not r.get("error"):err(f"load-results: {b}GB @ {ctx} failed without error")

ts=load("thread-sweep.csv");best_threads={}
if ts is not None:
 pairs=[];by_host_threads={}
 for r in ts:
  host=r.get("host");t=i(r["threads"]);rep=i(r.get("rep",1));pairs.append((host,rep,t))
  if host not in ("A","C"):err(f"thread-sweep: invalid host {host}")
  by_host_threads.setdefault(host,{}).setdefault(t,[]).append(float(r["tg_tok_s"]))
  if t<=0 or float(r["pp_tok_s"])<=0 or float(r["tg_tok_s"])<=0:err("thread-sweep: non-positive threads/speed")
 if len(pairs)!=len(set(pairs)):err("thread-sweep: duplicate host/rep/thread row")
 if not ts:err("thread-sweep: no rows")
 for host,grid in by_host_threads.items():
  if host=="C" and any(set(i(r["rep"]) for r in ts if r.get("host")==host and i(r["threads"])==t)!={1,2} for t in grid):err("thread-sweep: host C needs reps 1 and 2 for every thread count")
  med={t:sorted(v)[len(v)//2] if len(v)%2 else sum(sorted(v)[len(v)//2-1:len(v)//2+1])/2 for t,v in grid.items()}
  best_threads[host]=max(med,key=med.get)
 if best_threads.get("A")!=16:err("thread-sweep: host A best thread count should remain 16")

br=load("bench-results.csv");bench_seen={}
if br is not None:
 for r in br:
  b=i(r["budget_gb"]);ctx=i(r["ctx"]);d=i(r["depth"]);rep=i(r["rep"]);host=r.get("host","");k=(host,b,ctx,d,rep)
  if host not in ("A","B","C"):err(f"bench: invalid host label {host!r} at {k}")
  if host=="A" and rep!=1:err(f"bench: host A rows must be rep 1 at {k}")
  if host=="B" and rep not in (2,3):err(f"bench: host B rows must be rep 2 or 3 at {k}")
  if host=="C" and rep not in (1,2,3):err(f"bench: invalid host C round/rep at {k}")
  if host=="C":
   if i(r.get("round",0))!=rep:err(f"bench: host C round must match rep at {k}")
   if float(r.get("probe_gbps",0) or 0)<=0:err(f"bench: host C row missing positive probe_gbps at {k}")
  expected_host="A" if rep==1 else "B"
  if host in ("A","B") and host!=expected_host:err(f"bench: {k} host must be {expected_host}")
  bench_seen[k]=bench_seen.get(k,0)+1
  if i(r["fill_tokens"])!=d:err(f"bench: fill_tokens != depth at {k}")
  if i(r["n_threads"])<=0:err(f"bench: invalid n_threads at {k}")
  expected_t=best_threads.get("C") if host=="C" else best_threads.get("A")
  if expected_t is not None and i(r["n_threads"])!=expected_t:err(f"bench: n_threads does not match thread-sweep best T at {k}")
  if b in chosen and ctx!=i(chosen[b]["ctx"]):err(f"bench: ctx does not match selected calibration ctx for {b}GB")
  allowed=DEPTHS_32 if ctx==32768 else DEPTHS_128
  if d not in allowed:err(f"bench: invalid depth {d} for ctx={ctx}")
  if float(r["pp_tok_s"])<=0 or float(r["tg_tok_s"])<=0:err(f"bench: non-positive speed at {k}")
  load_host="C" if host=="C" else "0"
  if (load_host,b,ctx) not in loads_by or loads_by[(load_host,b,ctx)]["loaded"]!="1":err(f"bench: row without successful load for host {load_host} at {k}")
 for k,n in bench_seen.items():
  if n>1:err(f"bench: duplicate row {k}")
 for b,r in chosen.items():
  ctx=i(r["ctx"])
  if loads_by.get(("0",b,ctx),{}).get("loaded")!="1":continue
  grid=DEPTHS_32 if ctx==32768 else DEPTHS_128
  for d in {d for d in grid if d<ctx}:
    for rep in REPS:
     host="A" if rep==1 else "B"
     if (host,b,ctx,d,rep) not in bench_seen:err(f"bench: missing {b}GB ctx={ctx} depth={d} host={host} rep={rep}")
  if any(k[0]=="C" for k in bench_seen):
   for b,r in chosen.items():
    ctx=i(r["ctx"]);grid=DEPTHS_32 if ctx==32768 else DEPTHS_128
    c_load=loads_by.get(("C",b,ctx))
    if not c_load:err(f"load-results: missing host C 128K confirmation for {b}GB")
    elif c_load["loaded"]!="1" or i(c_load["peak_vram_mib"])>b*1024-MARGIN:err(f"load-results: host C {b}GB 128K load did not pass margin")
    for d in {d for d in grid if d<ctx}:
     for rep in REPS:
      if ("C",b,ctx,d,rep) not in bench_seen:err(f"bench: missing host C {b}GB ctx={ctx} depth={d} round={rep}")

ppl=load("ppl-results.csv")
if ppl is not None:
 seen={}
 for r in ppl:
  if r.get("host")!="0":err("ppl: rows must be host 0")
  b=i(r["budget_gb"])
  if b in seen:err(f"ppl: duplicate row for {b}GB")
  seen[b]=r
  if float(r["ppl"] or 0)<=0:err(f"ppl: non-positive/missing perplexity for {b}GB")
  if i(r["ctx"])!=2048 or i(r["chunks"])!=8:err(f"ppl: expected ctx=2048 chunks=8 for {b}GB")
 if 24 not in seen:err("ppl: missing 24GB baseline row")
 for b in chosen:
  if b not in seen:err(f"ppl: missing chosen {b}GB row")
  elif i(seen[b]["n_cpu_moe"])!=i(chosen[b]["n_cpu_moe"]):err(f"ppl: N mismatch for {b}GB")
  elif i(seen[b]["op_offload"])!=int(i(chosen[b]["n_cpu_moe"])==0):err(f"ppl: op_offload should be {int(i(chosen[b]['n_cpu_moe'])==0)} for {b}GB")

if errors:
 print("FAIL");[print(" -",x) for x in errors];sys.exit(1)
print(f"PASS budgets={sorted(chosen)} depth_rows={len(br or [])} ppl_rows={len(ppl or [])} thread_sweep_rows={len(ts or [])} T={best_threads.get('A')}")
