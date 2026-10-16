#!/usr/bin/env python3
"""Print all headline metrics from the configured study CSVs."""
import csv, json, statistics, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'DATA/study-config.json').read_text())
loads=list(csv.DictReader((ROOT/'DATA/load-results.csv').open()))
benches=list(csv.DictReader((ROOT/'DATA/bench-results.csv').open()))
vram=int(re.search(r'(\d+)GB', cfg['gpu']).group(1))*1024
models=list(cfg['models'])
print('== Context ceiling and card headroom')
ceilings={}
for m in models:
 r=next(x for x in loads if x['model']==m and x['is_ceiling']=='1'); ceilings[m]=int(r['ctx_size'])
 peak=int(r['peak_vram_load_mib']); head=vram-peak
 print(f"{m}: ceiling {ceilings[m]:,} tokens; peak {peak:,} MiB; headroom {head:,} MiB ({head/vram*100:.2f}%)")
print('== Load buffer sum residual versus peak VRAM (successful rows)')
for r in loads:
 if r['loaded_full_gpu']=='1':
  used=sum(float(r[k]) for k in ('model_buffer_mib','kv_buffer_mib','rs_buffer_mib','compute_buffer_mib')); peak=float(r['peak_vram_load_mib'])
  print(f"{r['model']} {int(r['ctx_size']):,}: buffers {used:,.2f} MiB; peak {peak:,.0f} MiB; residual {peak-used:,.2f} MiB")
print('== KV cache bytes per token (each successful load row)')
for m in models:
 vals=[]
 for r in loads:
  if r['model']==m and r['loaded_full_gpu']=='1':
   b=float(r['kv_buffer_mib'])*1048576/int(r['ctx_size']); vals.append(b)
   print(f"{m} {int(r['ctx_size']):,}: {float(r['kv_buffer_mib']):,.2f} MiB / {int(r['ctx_size']):,} = {b:,.2f} bytes/token")
 print(f"{m}: mean {statistics.mean(vals):,.2f} bytes/token")
print(f"Qwen/Nemotron mean KV bytes/token ratio: {statistics.mean([float(r['kv_buffer_mib'])*1048576/int(r['ctx_size']) for r in loads if r['model']=='qwen' and r['loaded_full_gpu']=='1'])/statistics.mean([float(r['kv_buffer_mib'])*1048576/int(r['ctx_size']) for r in loads if r['model']=='nemotron' and r['loaded_full_gpu']=='1']):.3f}")
print('== Speed and retention versus mean depth-0 baseline')
for metric,label in [('decode_tps','decode'),('prompt_tps','prompt')]:
 means={}
 for m in models:
  base=[float(r[metric]) for r in benches if r['model']==m and int(r['depth_tokens'])==0]
  means[m]=statistics.mean(base)
  print(f"{m} {label} depth-0 mean {means[m]:.4f} tok/s; range {min(base):.4f}–{max(base):.4f}")
  for r in benches:
   if r['model']==m and int(r['depth_tokens'])>0:
    print(f"{m} {label} depth {int(r['depth_tokens']):,} ({r['depth_label']}): {float(r[metric]):.4f} tok/s = {float(r[metric])/means[m]*100:.2f}% retained; single run")
 for depth in (0,65536,131072):
  vals={m:([float(r[metric]) for r in benches if r['model']==m and int(r['depth_tokens'])==depth]) for m in models}
  if all(vals.values()):
   n=statistics.mean(vals['nemotron']); q=statistics.mean(vals['qwen'])
   print(f"Nemotron/Qwen {label} ratio at {depth:,}: {n/q:.3f} (N {n:.4f} / Q {q:.4f})")
 n90=next(float(r[metric]) for r in benches if r['model']=='nemotron' and r['depth_label']=='ceiling90'); q90=next(float(r[metric]) for r in benches if r['model']=='qwen' and r['depth_label']=='ceiling90')
 print(f"Nemotron/Qwen {label} ratio at their respective ceiling90 points: {n90/q90:.3f} (N {n90:.4f} / Q {q90:.4f}; depths differ by model ceiling)")
