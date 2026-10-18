#!/usr/bin/env python3
"""Run the T=16 rep-2/3 llama-bench cells on the configured pod."""
import argparse, csv, json, os, pathlib, subprocess, sys, threading, time

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'DATA'; RAW=ROOT/'_internal'/'raw'
MODEL=DATA/'NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf'
BENCH=ROOT/'llama.cpp'/'build'/'bin'/'llama-bench'
FIELDS='budget_gb n_cpu_moe ctx depth fill_tokens rep n_threads pp_tok_s tg_tok_s peak_vram_mib'.split()
CHOSEN={8:82,12:60,16:40,24:0}
DEPTHS=(0,32768,65536,117964)
CREATED=float(os.environ.get('POD_CREATED_EPOCH','0'))
CAP=int(os.environ.get('GPU_CAP_SECONDS','7200'))
RESERVE=int(os.environ.get('SYNC_RESERVE_SECONDS','300'))

def sample(stop, peaks, samples):
    while not stop.is_set():
        gpu=peaks.get('gpu',0);used=peaks.get('ram',0)
        try:
            s=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True,timeout=2)
            gpu=int(s.splitlines()[0].strip());peaks['gpu']=max(peaks.get('gpu',0),gpu)
        except Exception: pass
        try:
            mem={k:int(v) for k,v in (x.split(':',1) for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if ':' in x)}
            used=(mem['MemTotal']-mem.get('MemAvailable',mem['MemTotal']))//1024
            peaks['ram']=max(peaks.get('ram',0),used)
        except Exception: pass
        samples.append((time.time(),gpu,used))
        stop.wait(.2)

def run(b,n,ctx,depth,reps,tag):
    RAW.mkdir(parents=True,exist_ok=True)
    log=RAW/f'{tag}-b{b}-n{n}-ctx{ctx}-d{depth}.log'
    samples=RAW/f'{tag}-b{b}-n{n}-ctx{ctx}-d{depth}-vram.csv'
    cmd=[str(BENCH),'-m',str(MODEL),'-ngl','99','--n-cpu-moe',str(n),'-fa','on','-ctk','q8_0','-ctv','q8_0','-t','16','-p','512','-n','128','-d',str(depth),'-r',str(reps),'-o','json']
    env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']='0'
    stop=threading.Event();peaks={};sample_rows=[];t=threading.Thread(target=sample,args=(stop,peaks,sample_rows),daemon=True);t.start()
    with log.open('w') as f:
        try:
            remaining=max(1,int(CREATED+CAP-RESERVE-time.time())) if CREATED else 1
            p=subprocess.run(cmd,cwd=ROOT/'llama.cpp',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=remaining)
            f.write(p.stdout);f.flush()
        except subprocess.TimeoutExpired as e:
            f.write((e.stdout or '') if isinstance(e.stdout,str) else '')
            f.write('\nBUDGET TIMEOUT\n');p=None
    stop.set();t.join()
    with samples.open('w') as sf:
        sf.write('epoch,gpu_used_mib,host_ram_used_mib\n')
        for row in sample_rows:sf.write(f'{row[0]:.3f},{row[1]},{row[2]}\n')
    result={"ok":False,"peak":peaks.get('gpu',0)}
    if p is not None and p.returncode==0:
        try:
            # llama-bench's CUDA backend writes its two startup diagnostics to
            # stdout before the JSON array; decode the JSON payload only.
            start=p.stdout.find('[')
            if start < 0: raise ValueError('llama-bench JSON array missing from stdout')
            payload=json.loads(p.stdout[start:])
            pp=next(x for x in payload if int(x.get('n_prompt',-1))==512 and int(x.get('n_gen',-1))==0 and int(x.get('n_depth',-1))==depth)
            tg=next(x for x in payload if int(x.get('n_gen',-1))==128 and int(x.get('n_prompt',-1))==0 and int(x.get('n_depth',-1))==depth)
            pps=pp.get('samples_ts',[]);tgs=tg.get('samples_ts',[])
            if len(pps)!=reps or len(tgs)!=reps: raise ValueError(f'expected {reps} samples, got prompt={len(pps)} decode={len(tgs)}')
            result.update(ok=True,pps=pps,tgs=tgs,peak=peaks.get('gpu',0))
        except Exception as e: result['error']=str(e)
    else: result['error']='bench process failed or timed out'
    if not result['ok']:
        with (RAW/'bench-failures.csv').open('a',newline='') as f:
            w=csv.writer(f)
            if f.tell()==0:w.writerow(['budget_gb','n_cpu_moe','ctx','depth','rep','error'])
            w.writerow([b,n,ctx,depth,tag,result.get('error','bench failed')])
    return result

def append_rows(b,n,ctx,depth,result,rep_base):
    if not result['ok']: return
    path=DATA/'bench-results.csv';exists=path.exists()
    with path.open('a',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        if not exists:w.writeheader()
        for ix,(pp,tg) in enumerate(zip(result['pps'],result['tgs'])):
            w.writerow(dict(budget_gb=b,n_cpu_moe=n,ctx=ctx,depth=depth,fill_tokens=depth,rep=rep_base+ix,n_threads=16,pp_tok_s=pp,tg_tok_s=tg,peak_vram_mib=result['peak']))
        f.flush();os.fsync(f.fileno())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['quick','budget']);ap.add_argument('--budget',type=int);a=ap.parse_args()
    if not CREATED:raise SystemExit('POD_CREATED_EPOCH required')
    if not MODEL.exists() or not BENCH.exists():raise SystemExit('model or llama-bench missing')
    if a.mode=='quick':
        x=run(12,60,131072,0,1,'quick-check')
        if x['ok']:
            q=RAW/'quick-check.csv'
            with q.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['budget_gb','n_cpu_moe','ctx','depth','rep','pp_tok_s','tg_tok_s','peak_vram_mib']);w.writerow([12,60,131072,0,1,x['pps'][0],x['tgs'][0],x['peak']])
            print(f"quick check: pp={float(x['pps'][0]):.2f} tg={float(x['tgs'][0]):.2f} peak={x['peak']} MiB",flush=True)
            return 0
        print('quick check FAILED and logged; continuing to bench: '+str(x.get('error')),file=sys.stderr,flush=True);return 0
    b=a.budget
    if b not in CHOSEN:raise SystemExit('budget must be one of 8,12,16,24')
    for d in DEPTHS:
        rem=CREATED+CAP-RESERVE-time.time()
        if rem<=30:
            print(f'CAP GUARD: stopping before budget={b} depth={d}; remaining={rem:.0f}s',flush=True);break
        print(f'bench start budget={b} N={CHOSEN[b]} depth={d} reps=2 cap_remaining={rem:.0f}s',flush=True)
        x=run(b,CHOSEN[b],131072,d,2,'bench-r23')
        if x['ok']:
            append_rows(b,CHOSEN[b],131072,d,x,2)
            print(f"bench complete b={b} depth={d}: rep2 pp={float(x['pps'][0]):.3f} tg={float(x['tgs'][0]):.3f}; rep3 pp={float(x['pps'][1]):.3f} tg={float(x['tgs'][1]):.3f}",flush=True)
        else:print(f"bench failed b={b} depth={d}; logged and continuing: {x.get('error')}",file=sys.stderr,flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
