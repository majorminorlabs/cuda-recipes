#!/usr/bin/env python3
"""Rebuild numerical measurement rows from public evidence and run roles."""
from pathlib import Path
import argparse,csv,gzip,json,io
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
data=json.loads((ROOT/'results.json').read_text());runs=json.loads((ROOT/'run-index.json').read_text());rows=[]
if any(r['system'] not in {'rtx3090','rtx3090-depth'} or r['model'] not in {'base','adq4'} for r in runs):
    raise SystemExit('Unexpected run scope: expected RTX 3090 and the two Q4 artifacts')
for run in runs:
    if run['status']!='measured':continue
    raw=json.loads(gzip.decompress((ROOT/run['stdout']).read_bytes()).decode())
    for r in raw:
        metric='pp512' if r['n_prompt']==512 and r['n_gen']==0 else ('tg128' if run['kind'] in {'primary','tuning'} else 'decode128')
        rows.append({'id':run['id']+'/'+metric+'/d'+str(r['n_depth']),'run':run['id'],
          'system':run['system'],'model':run['model'],'metric':metric,'kind':run['kind'],'selection':run['selection'],
          'depth_tokens':r['n_depth'],'mean_tok_s':r['avg_ts'],'sample_stddev_tok_s':r['stddev_ts'],
          'samples_tok_s':r['samples_ts'],'repetitions':len(r['samples_ts']),
          'settings':{k:r[k] for k in r if k.startswith('n_') or k in ['type_k','type_v','flash_attn','fit_target','fit_min_ctx','backends','build_commit','build_number','repack','load_mode','lazy_mode','no_host','tensor_buft_overrides']},
          'raw_row':r,'stdout':run['stdout'],'metadata':run['metadata']})
if args.check:
    if rows!=data['measurements']:raise SystemExit('Measurement rows do not rebuild exactly')
    expected=io.StringIO();keys=['id','system','model','metric','kind','selection','depth_tokens','mean_tok_s','sample_stddev_tok_s','repetitions','stdout','metadata']
    w=csv.DictWriter(expected,fieldnames=keys,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    if expected.getvalue()!=(ROOT/'results.csv').read_text():raise SystemExit('CSV rows do not rebuild exactly')
    print(f'PASS: {len(rows)} measurement rows rebuild exactly from public evidence')
else:
    data['measurements']=rows;(ROOT/'results.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    with (ROOT/'results.csv').open('w',newline='') as f:
        keys=['id','system','model','metric','kind','selection','depth_tokens','mean_tok_s','sample_stddev_tok_s','repetitions','stdout','metadata']
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    print(f'Rebuilt {len(rows)} measurement rows; run summarize.py to refresh tables')
