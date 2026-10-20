#!/usr/bin/env python3
"""Phase 0 capture, calibration, load, and bounded depth sweep."""
import argparse, csv, hashlib, json, os, pathlib, re, socket, subprocess, sys, tempfile, threading, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"DATA"; RAW=ROOT/"_internal"/"raw"
COMMIT="620d2225cc436ab0b001e3200e590e3b286ef9ab"
MODEL=os.environ.get("MODEL_FILE",""); MODEL_SHA=os.environ.get("MODEL_SHA256","91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75")
SERVER=os.environ.get("LLAMA_SERVER","llama-server"); BENCH=os.environ.get("LLAMA_BENCH","llama-bench")
MARGIN=500; CAP_SECONDS=int(os.environ.get("GPU_CAP_SECONDS","7200")); RESERVE_SECONDS=int(os.environ.get("SYNC_RESERVE_SECONDS","600")); WORK_CAP=CAP_SECONDS-RESERVE_SECONDS; DEPTHS_128=(0,32768,65536,117964); DEPTHS_32=(0,16384,29491); BUDGET_ORDER=(8,12,16,24)

def rawdir(): RAW.mkdir(parents=True,exist_ok=True)
def csv_append(path, fields, row):
    path.parent.mkdir(parents=True,exist_ok=True); exists=path.exists()
    with path.open("a",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); 
        if not exists: w.writeheader()
        w.writerow(row); f.flush(); os.fsync(f.fileno())
def data_append(name,fields,row): csv_append(DATA/name,fields,row)
def pod_elapsed():
    created=float(os.environ.get("POD_CREATED_EPOCH","0"))
    if not created: raise RuntimeError("POD_CREATED_EPOCH must be set from the actual pod creation timestamp")
    return max(0,time.time()-created)
def mem_stats():
    p=pathlib.Path("/proc/meminfo")
    if p.exists():
        m=dict(re.findall(r"^(\w+):\s+(\d+)",p.read_text(),re.M))
        return int(m["MemTotal"])//1024,(int(m["MemTotal"])-int(m.get("MemAvailable",m["MemTotal"])))//1024
    try: total=int(subprocess.check_output(["sysctl","-n","hw.memsize"],text=True))//1024//1024
    except Exception: total=0
    return total,total

def sample_loop(stop,out,peaks,interval=.4):
    gpu=ram=0
    if out.tell()==0: out.write("epoch,gpu_used_mib,host_ram_used_mib,pcie_gen_current,pcie_width_current\n");out.flush()
    while not stop.is_set():
        try:
            q=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,pcie.link.gen.current,pcie.link.width.current","--format=csv,noheader,nounits"],text=True,timeout=interval).splitlines()[0].split(",")
            gpu=max(gpu,int(q[0].strip())); _,used=mem_stats();ram=max(ram,used)
            out.write(f"{time.time():.3f},{q[0].strip()},{ram},{q[1].strip() if len(q)>1 else ''},{q[2].strip() if len(q)>2 else ''}\n");out.flush()
        except Exception as e: out.write(f"sampler_error,{e}\n");out.flush()
        stop.wait(interval)
    peaks.update(gpu=max(gpu,peaks.get("gpu",0)),ram=max(ram,peaks.get("ram",0)))

def start_sampler(path):
    rawdir(); f=path.open("a"); stop=threading.Event(); peaks={}
    t=threading.Thread(target=sample_loop,args=(stop,f,peaks),daemon=True);t.start();return stop,t,peaks,f
def finish_sampler(stop,t,f): stop.set();t.join();f.close()
def sample_now(peaks):
    try:
        v=int(subprocess.check_output(["nvidia-smi","--query-gpu=memory.used","--format=csv,noheader,nounits"],text=True,timeout=2).splitlines()[0].split(",")[0])
        _,r=mem_stats();peaks["gpu"]=max(v,peaks.get("gpu",0));peaks["ram"]=max(r,peaks.get("ram",0))
    except Exception:pass

def host():
    if not MODEL: raise RuntimeError("Set MODEL_FILE to the pinned Bolt GGUF")
    h=hashlib.sha256()
    with open(MODEL,"rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    if h.hexdigest()!=MODEL_SHA: raise RuntimeError("Model SHA-256 does not match pinned artifact")
    def sh(*a):
        try:return subprocess.check_output(a,text=True,stderr=subprocess.DEVNULL).strip()
        except Exception:return ""
    gpu=sh("nvidia-smi","--query-gpu=name,memory.total,driver_version,pcie.link.gen.max,pcie.link.width.max","--format=csv,noheader,nounits").split(",")
    gpu=(gpu+["unknown"]*5)[:5]; lscpu=sh("bash","-lc","lscpu")
    cpu=next((x.split(":",1)[1].strip() for x in lscpu.splitlines() if x.startswith("Model name:")),"unknown")
    def cpu_num(key):
        m=re.search(r"^"+re.escape(key)+r":\s*(\d+)",lscpu,re.M);return int(m.group(1)) if m else None
    cuda=re.search(r"release\s+(\d+\.\d+)",sh("nvcc","--version"))
    total,_=mem_stats()
    dataset=os.environ.get("WIKITEXT_FILE","")
    if not dataset or not pathlib.Path(dataset).is_file(): raise RuntimeError("Set WIKITEXT_FILE to the Wikitext-2 test file")
    dh=hashlib.sha256(pathlib.Path(dataset).read_bytes()).hexdigest()
    obj={"gpu_name":gpu[0].strip(),"gpu_vram_mib":int(gpu[1]),"driver_version":gpu[2].strip(),"cuda_version":cuda.group(1) if cuda else None,
      "cpu_model":cpu,"cpu_cores":(cpu_num("Core(s) per socket") or os.cpu_count())*(cpu_num("Socket(s)") or 1),"cpu_threads":os.cpu_count(),
      "ram_total_mib":total,"ram_speed_mts":None,"pcie_gen":int(gpu[3]) if gpu[3].strip().isdigit() else None,
      "pcie_width":int(gpu[4]) if gpu[4].strip().isdigit() else None,"llama_cpp_commit":COMMIT,"model_file":pathlib.Path(MODEL).name,
      "model_sha256":h.hexdigest(),"wikitext_file":pathlib.Path(dataset).name,"wikitext_sha256":dh,"run_started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    DATA.mkdir(exist_ok=True);(DATA/"host.json").write_text(json.dumps(obj,indent=2)+"\n")

def serve(n,ctx,budget,timeout):
    if not MODEL: raise RuntimeError("Set MODEL_FILE")
    with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    logpath=RAW/f"server-n{n}-ctx{ctx}.log";rawdir()
    cmd=[SERVER,"-m",MODEL,"--host","127.0.0.1","--port",str(port),"-ngl","99","--n-cpu-moe",str(n),"--ctx-size",str(ctx),"-fa","on","-ctk","q8_0","-ctv","q8_0","-np","1"]
    env=os.environ.copy();env["FAKE_BUDGET_GB"]=str(budget);env["FAKE_STATE_FILE"]=str(pathlib.Path(tempfile.gettempdir())/"cuda004-fake-vram.json")
    try:pathlib.Path(env["FAKE_STATE_FILE"]).unlink()
    except FileNotFoundError:pass
    log=open(logpath,"w");p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
    stop,t,peaks,sf=start_sampler(RAW/"sampler.csv");t0=time.monotonic();ready=False;time.sleep(.45)
    try:
        while time.monotonic()-t0<timeout:
            if p.poll() is not None:break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=2) as r:
                    if r.status==200:
                        ready=True
                        req=urllib.request.Request(f"http://127.0.0.1:{port}/completion",data=json.dumps({"prompt":"OK","n_predict":8}).encode(),headers={"Content-Type":"application/json"})
                        try:urllib.request.urlopen(req,timeout=60).read()
                        except Exception:pass
                        time.sleep(.45);break
            except Exception:pass
            time.sleep(.2)
        if p.poll() is None and not ready and time.monotonic()-t0>=timeout:p.terminate();p.wait(timeout=10)
    finally:
        sample_now(peaks);finish_sampler(stop,t,sf);log.flush();log.close()
    text=logpath.read_text(errors="replace")
    error=next((line.strip() for line in text.splitlines() if "error" in line.lower()),"")
    if not ready and not error:error=f"server failed or readiness timeout ({p.returncode})"
    return p,time.monotonic()-t0,peaks.get("gpu",0),peaks.get("ram",0),ready,error

def stop_server(p):
    if p and p.poll() is None:p.terminate();p.wait(timeout=20)

CAL_FIELDS="budget_gb n_cpu_moe ctx loaded peak_vram_mib host_ram_peak_mib chosen notes".split()
PROBE_CACHE={}
def write_cal(row): data_append("calibration.csv",CAL_FIELDS,row)
def mark_chosen(b,n,ctx):
    path=DATA/"calibration.csv";rows=list(csv.DictReader(path.open()))
    found=False
    for r in reversed(rows):
        if int(r["budget_gb"])==b and int(r["n_cpu_moe"])==n and int(r["ctx"])==ctx:
            r["chosen"]="1";found=True;break
    if not found:raise RuntimeError(f"selected N={n} missing from calibration rows")
    with path.open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=CAL_FIELDS);w.writeheader();w.writerows(rows)

def probe(b,n,ctx,timeout):
    key=(b,n,ctx)
    if key in PROBE_CACHE:return PROBE_CACHE[key]
    p,_,gpu,ram,ready,error=serve(n,ctx,b,timeout);stop_server(p)
    loaded=ready and not error
    write_cal(dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,loaded=int(loaded),peak_vram_mib=gpu,host_ram_peak_mib=ram,chosen=0,notes=error or ("fits" if gpu<=b*1024-MARGIN else "over target")))
    PROBE_CACHE[key]=(loaded,gpu,ram,error);return PROBE_CACHE[key]

def search_n(b,ctx,start,timeout):
    lo=start;hi=89
    while lo<hi:
        mid=(lo+hi)//2;loaded,gpu,_,_=probe(b,mid,ctx,timeout)
        if loaded and gpu<=b*1024-MARGIN:hi=mid
        else:lo=mid+1
    # Final verification is also the unique chosen row.
    loaded,gpu,_,_=probe(b,lo,ctx,timeout)
    if loaded and gpu<=b*1024-MARGIN:mark_chosen(b,lo,ctx);return lo
    return None

def calibrate(args):
    pod_elapsed();prev=0
    for b in (24,16,12,8):
        if b==24:
            loaded,gpu,_,_=probe(b,0,131072,args.load_timeout)
            chosen=0 if loaded and gpu<=24*1024-MARGIN else None
            if chosen is not None:mark_chosen(24,0,131072)
        else:chosen=search_n(b,131072,prev,args.load_timeout)
        if chosen is not None:
            prev=chosen;continue
        if b==8:
            print("8GB has no N within the 128K VRAM target; retrying calibration at 32K",flush=True)
            fallback=search_n(8,32768,prev,args.load_timeout)
            if fallback is None:print("8GB also failed calibration at 32K; recording the budget as unavailable",flush=True)
            else:prev=fallback

def chosen_calibration():
    rows=list(csv.DictReader((DATA/"calibration.csv").open()))
    return {int(r["budget_gb"]):r for r in rows if r["chosen"]=="1"}

def load_sweep(args):
    chosen=chosen_calibration();fields="budget_gb n_cpu_moe ctx loaded peak_vram_mib host_ram_peak_mib error".split()
    for b,r in sorted(chosen.items()):
        n=int(r["n_cpu_moe"])
        for ctx in (32768,131072,262144):
            p,_,gpu,ram,ready,error=serve(n,ctx,b,args.load_timeout);stop_server(p)
            loaded=ready and not error and gpu<=b*1024-MARGIN
            if ready and gpu>b*1024-MARGIN:error="exceeds budget at chosen N"
            if not loaded and not error:error="load failed"
            data_append("load-results.csv",fields,dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,loaded=int(loaded),peak_vram_mib=gpu if loaded else "",host_ram_peak_mib=ram if loaded else "",error="" if loaded else error))

def bench_one(b,n,ctx,depth,rep,timeout,threads=128):
    cmd=[BENCH,"-m",MODEL,"-ngl","99","--n-cpu-moe",str(n),"-fa","on","-ctk","q8_0","-ctv","q8_0","-t",str(threads),"-p","512","-n","128","-d",str(depth),"-r","1","-o","json"]
    env=os.environ.copy();env.update(FAKE_N=str(n),FAKE_BENCH_CTX=str(ctx),FAKE_STATE_FILE=str(pathlib.Path(tempfile.gettempdir())/"cuda004-fake-vram.json"))
    try:pathlib.Path(env["FAKE_STATE_FILE"]).unlink()
    except FileNotFoundError:pass
    result,peaks=captured_run(cmd,timeout,RAW/"sampler.csv",env)
    rawdir();base=f"bench-{b}-t{threads}-ctx{ctx}-depth{depth}-rep{rep}"
    (RAW/f"{base}.stdout").write_text(result.stdout);(RAW/f"{base}.stderr").write_text(result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.strip() or f"llama-bench exited {result.returncode}")
    rows=json.loads(result.stdout)
    pp=next(float(x.get("avg_ts",0)) for x in rows if int(x.get("n_prompt",-1))==512 and int(x.get("n_gen",-1))==0 and int(x.get("n_depth",-1))==depth)
    tg=next(float(x.get("avg_ts",0)) for x in rows if int(x.get("n_gen",-1))==128 and int(x.get("n_prompt",-1))==0 and int(x.get("n_depth",-1))==depth)
    if pp<=0 or tg<=0 or not peaks.get("gpu"):raise RuntimeError("invalid speeds or missing VRAM sample")
    return pp,tg,peaks["gpu"]

def thread_sweep(args):
    chosen=chosen_calibration(); n=int(chosen[12]["n_cpu_moe"]); ctx=int(chosen[12]["ctx"])
    nproc=int(subprocess.check_output(["nproc"],text=True).strip())
    values=list(dict.fromkeys((4,8,16,max(1,nproc//2),nproc)))
    fields=["threads","pp_tok_s","tg_tok_s"]
    out=DATA/"thread-sweep.csv"
    with out.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for threads in values:
        remaining=max(0,WORK_CAP-pod_elapsed())
        if remaining<=0:
            print("WATCHDOG: no GPU time remains for thread-sweep",flush=True);break
        t0=time.monotonic()
        pp,tg,peak=bench_one(12,n,ctx,0,1,min(1800,max(1,int(remaining))),threads)
        data_append("thread-sweep.csv",fields,dict(threads=threads,pp_tok_s=pp,tg_tok_s=tg))
        print(f"thread sweep t={threads}: pp={pp:.3f} tg={tg:.3f} tok/s, peak={peak} MiB, elapsed={time.monotonic()-t0:.1f}s",flush=True)
    rows=list(csv.DictReader(out.open()))
    if len(rows)!=len(values): raise RuntimeError(f"thread sweep incomplete: got {len(rows)} of {len(values)} thread counts")
    best=max(rows,key=lambda r:float(r["tg_tok_s"]))
    (ROOT/"_internal"/"thread-sweep-best.txt").write_text(best["threads"]+"\n")
    print(f"Selected T={best['threads']} by maximum decode",flush=True)

def bench(args):
    created=float(os.environ.get("POD_CREATED_EPOCH","0"));remaining=max(0,WORK_CAP-(time.time()-created)) if created else 0
    if remaining<=0:print("WATCHDOG: no GPU time remains for the bench sweep",flush=True);return
    chosen=chosen_calibration();loads=list(csv.DictReader((DATA/"load-results.csv").open()))
    plans=[]
    for b in BUDGET_ORDER:
        if b not in chosen:continue
        row=chosen[b];ctx=int(row["ctx"]);n=int(row["n_cpu_moe"])
        if not any(int(x["budget_gb"])==b and int(x["ctx"])==ctx and x["loaded"]=="1" for x in loads):continue
        grid=DEPTHS_32 if ctx==32768 else DEPTHS_128
        ds=[d for d in grid if d<ctx]
        if ds:plans.append((b,n,ctx,ds))
    if not plans:raise RuntimeError("no loaded chosen context is eligible for bench")
    tfile=ROOT/"_internal"/"thread-sweep-best.txt"
    if not tfile.exists(): raise RuntimeError("run thread-sweep before bench")
    threads=int(tfile.read_text().strip())
    fields="budget_gb n_cpu_moe ctx depth fill_tokens rep n_threads pp_tok_s tg_tok_s peak_vram_mib".split()
    failfields="budget_gb n_cpu_moe ctx depth rep error".split()
    # Time each budget's own depth-zero cell first, in ascending budget order.
    baselines={}; estimates={};
    for b,n,ctx,ds in plans:
        t0=time.monotonic()
        try:
            pp,tg,peak=bench_one(b,n,ctx,0,1,min(args.bench_timeout,max(1,int(remaining))),threads)
            elapsed=max(.01,time.monotonic()-t0);baselines[b]=(elapsed,pp,tg)
            data_append("bench-results.csv",fields,dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,depth=0,fill_tokens=0,rep=1,n_threads=threads,pp_tok_s=pp,tg_tok_s=tg,peak_vram_mib=peak))
            estimates[b]={0:elapsed*1.2}
            for d in ds:
                if d==0:continue
                # The depth setting requires processing that many prompt tokens
                # before the measured 512-token prompt / 128-token generation.
                # Use this budget's own depth-zero prompt rate for that fill cost.
                estimates[b][d]=(elapsed+d/max(1.0,pp))*1.2
        except Exception as e:
            rawdir();csv_append(RAW/"bench-failures.csv",failfields,dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,depth=0,rep=1,error=str(e)))
            print(f"BENCH FAILED and logged; continuing: {b}GB depth=0 rep=1: {e}",file=sys.stderr,flush=True)
    rep_cost=sum(sum(estimates.get(b,{}).get(d,0) for d in ds) for b,n,ctx,ds in plans)
    remaining=max(0,WORK_CAP-pod_elapsed())
    first_remaining=max(0,rep_cost-sum(v.get(0,0) for v in estimates.values()))
    reps_fit=(0 if remaining<first_remaining else min(3,1+int((remaining-first_remaining)//max(.01,rep_cost)))) if rep_cost>0 else 0
    projected=rep_cost*3
    print(f"Per-budget depth-zero pilots recorded. Projected remaining sweep (all 3 reps): {projected:.1f}s; remaining cap: {remaining:.1f}s; planned reps including depth-zero pilots: {reps_fit}.",flush=True)
    if projected>remaining: print("Projection exceeds remaining cap; running only complete repetitions that fit.",flush=True)
    for rep in range(1,reps_fit+1):
      for b,n,ctx,ds in plans:
       for depth in ds:
        if rep==1 and depth==0:continue
        remaining=max(0,WORK_CAP-pod_elapsed())
        if remaining<=0:print("WATCHDOG: remaining GPU-hour cap reached; sweep stopped",flush=True);return
        try:
            pp,tg,peak=bench_one(b,n,ctx,depth,rep,min(args.bench_timeout,max(1,int(remaining))),threads)
            data_append("bench-results.csv",fields,dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,depth=depth,fill_tokens=depth,rep=rep,n_threads=threads,pp_tok_s=pp,tg_tok_s=tg,peak_vram_mib=peak))
        except Exception as e:
            rawdir();csv_append(RAW/"bench-failures.csv",failfields,dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,depth=depth,rep=rep,error=str(e)))
            print(f"BENCH FAILED and logged; continuing: {b}GB ctx={ctx} depth={depth} rep={rep}: {e}",file=sys.stderr,flush=True)

def captured_run(cmd,timeout,sampler_file,env=None):
    stop,t,peaks,sf=start_sampler(sampler_file)
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env)
        return result,peaks
    finally:sample_now(peaks);finish_sampler(stop,t,sf)

def watchdog(test=False):
    created=float(os.environ.get("POD_CREATED_EPOCH","0"))
    if not created:raise SystemExit("Set POD_CREATED_EPOCH to the actual pod creation Unix timestamp")
    stop=os.environ.get("POD_STOP_CMD")
    if test:
        if not stop:raise SystemExit("POD_STOP_CMD is unset")
        print(f"WATCHDOG TEST: stop command resolved: {stop}",flush=True)
        return
    deadline=created+CAP_SECONDS
    sync=os.environ.get("POD_SYNC_CMD")
    # Reserve the final five minutes for a best-effort transfer, but never let
    # it extend the provider hard-stop deadline.
    sync_start=deadline-300
    while time.time()<sync_start:time.sleep(min(1,sync_start-time.time()))
    if sync:
        remaining=max(1,deadline-time.time())
        try:subprocess.run(["bash","-c",sync,"_",str(DATA)+"/",str(RAW)+"/"],check=False,timeout=remaining)
        except subprocess.TimeoutExpired:print("WATCHDOG: sync timed out at hard-stop deadline",flush=True)
    else:print("WATCHDOG: POD_SYNC_CMD unset; stopping without sync",flush=True)
    while time.time()<deadline:time.sleep(min(1,deadline-time.time()))
    if not stop:raise SystemExit("WATCHDOG EXPIRED but POD_STOP_CMD is unset; configure provider stop hook")
    subprocess.run(stop,shell=True,check=False);raise SystemExit("WATCHDOG HARD STOP: 2.0 hours since pod creation")

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True)
    sp.add_parser("host");wp=sp.add_parser("watchdog");wp.add_argument("--test",action="store_true")
    for c in ("calibrate","load","bench","thread-sweep"):
        p=sp.add_parser(c);p.add_argument("--load-timeout",type=int,default=900);p.add_argument("--bench-timeout",type=int,default=900)
    a=ap.parse_args()
    if a.cmd=="host":host()
    elif a.cmd=="watchdog":watchdog(a.test)
    else:{"calibrate":calibrate,"load":load_sweep,"bench":bench,"thread-sweep":thread_sweep}[a.cmd](a)
if __name__=="__main__":
    try:main()
    except (RuntimeError,subprocess.TimeoutExpired) as e:print(f"STOP: {e}",file=sys.stderr);sys.exit(2)
