#!/usr/bin/env python3
"""Print all primary/exploratory headline statistics from the frozen result tables."""
import csv, json, statistics as st
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'DATA'
answers=list(csv.DictReader((D/'answer-results.csv').open()))
prefills=list(csv.DictReader((D/'prefill-results.csv').open()))
questions={q['question_id']:q for q in map(json.loads,(D/'questions.jsonl').open())}
models=['qwen36_35b_a3b','nemotron','qwen38_27b']; lengths=['control','long_64k','long_128k']; tasks=['single_retrieval','multi_retrieval','aggregation','multi_hop']
name={'qwen36_35b_a3b':'Qwen3.6','nemotron':'Nemotron','qwen38_27b':'Qwen3.8'}
def pct(rows,col='correct'):
 return (sum(int(r[col] or 0) for r in rows),len(rows),100*sum(int(r[col] or 0) for r in rows)/len(rows) if rows else 0)
def rows_for(m,l=None,t=None): return [r for r in answers if r['model']==m and (l is None or r['length_label']==l) and (t is None or r['task_type']==t)]
print('ACCURACY content correct/total (%) by model x length x task')
for m in models:
 for l in lengths:
  print(name[m],l, ' | '.join(f'{t} {pct(rows_for(m,l,t))[0]}/{pct(rows_for(m,l,t))[1]} ({pct(rows_for(m,l,t))[2]:.1f}%)' for t in tasks))
print('\nSINGLE RETRIEVAL by nominal position (all lengths pooled; fraction range)')
for m in models:
 for pos in ['early','middle','late']:
  rr=[r for r in rows_for(m,t='single_retrieval') if r['position']==pos]
  fs=[f for r in rr for f in questions[r['question_id']].get('fact_fractions',[])]
  a=pct(rr); print(f'{name[m]} {pos}: {a[0]}/{a[1]} ({a[2]:.1f}%), fractions {min(fs):.3f}-{max(fs):.3f}')
print('\nMULTI-RETRIEVAL content vs exact-format')
for m in models:
 for l in lengths:
  rr=rows_for(m,l,'multi_retrieval'); c=pct(rr); s=pct(rr,'format_strict_correct'); print(f'{name[m]} {l}: content {c[0]}/{c[1]} ({c[2]:.1f}%); format_strict {s[0]}/{s[1]} ({s[2]:.1f}%)')
print('\nPREFILL mean seconds and prompt tokens by model x length')
for m in models:
 for l in lengths:
  rr=[r for r in prefills if r['model']==m and r['length_label']==l]
  print(f'{name[m]} {l}: {st.mean(float(r["prefill_s"]) for r in rr):.3f}s mean, {st.mean(int(r["prompt_tokens"]) for r in rr):.0f} tokens mean')
print('\nANSWER mean seconds and generated tokens; truncation / invalid JSON by model')
for m in models:
 rr=rows_for(m); print(f'{name[m]}: {st.mean(float(r["answer_s"]) for r in rr):.3f}s, {st.mean(int(r["generated_tokens"]) for r in rr):.1f} tokens; truncated={sum(r["failure_class"]=="truncated" for r in rr)}, invalid_json={sum(r["failure_class"]=="invalid_json" for r in rr)}')
print('\nFIT at 131072 and cache reuse')
fits=list(csv.DictReader((D/'fit-results.csv').open()))
for m in models:
 r=next(x for x in fits if x['model']==m); rr=rows_for(m); reuse=sum(int(x['cached_prompt_tokens'] or 0)>0 for x in rr); followups=sum(max(0,len([z for z in rr if z['doc_id']==doc])-1) for doc in {x['doc_id'] for x in rr})
 print(f'{name[m]}: full_gpu={r["loaded_full_gpu"]}, layers={r["layers_on_cuda"]}/{r["layers_total"]}, peak_vram={r["peak_vram_mib"]} MiB; cached follow-ups {reuse}/{followups} ({100*reuse/followups:.1f}%)')
print('\nCOST (recorded GPU hours x $0.50/hour)')
for label,h in [('primary',0.624),('exploratory-thinking-on',1.49)]: print(f'{label}: {h:.3f} GPU-h, ${h*.5:.3f}')
