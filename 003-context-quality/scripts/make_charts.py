#!/usr/bin/env python3
"""Regenerate the three 003 study charts from DATA CSVs."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'DATA'; OUT=ROOT/'CHARTS'; OUT.mkdir(exist_ok=True)
rows=list(csv.DictReader((D/'answer-results.csv').open()))
pref=list(csv.DictReader((D/'prefill-results.csv').open()))
models=['qwen36_35b_a3b','nemotron','qwen38_27b']; labels={'qwen36_35b_a3b':'Qwen3.6 35B-A3B','nemotron':'Nemotron 3.5 Bolt','qwen38_27b':'Qwen3.8 27B'}
colors={'qwen36_35b_a3b':'#7651a8','nemotron':'#ba4e25','qwen38_27b':'#2e65a0'}
lengths=['control','long_64k','long_128k']; xlabs=['Control','64K','128K']; tasks=['single_retrieval','multi_retrieval','aggregation','multi_hop']; tlabels=['Single retrieval','Multi retrieval','Aggregation','Multi-hop']
INK,MUTED,GRID,SURF='#0a0a08','#514e44','#b8ad96','#e7dfcc'
plt.rcParams.update({'font.family':'DejaVu Sans Mono','font.size':9,'axes.edgecolor':GRID,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,'text.color':INK,'figure.facecolor':SURF,'axes.facecolor':SURF,'svg.fonttype':'none'})
def clean(ax,axis='y'):
 for s in ('top','right','left'): ax.spines[s].set_visible(False)
 ax.grid(axis=axis,color=GRID,lw=.7); ax.set_axisbelow(True); ax.tick_params(length=0)
def save(fig,stem):
 fig.savefig(OUT/(stem+'.svg'),bbox_inches='tight'); fig.savefig(OUT/(stem+'.png'),dpi=180,bbox_inches='tight'); plt.close(fig)
def acc(m,l,t):
 rr=[r for r in rows if r['model']==m and r['length_label']==l and r['task_type']==t]
 return sum(int(r['correct']) for r in rr)/len(rr)*100 if rr else 0
# a: small multiples by task
fig,axs=plt.subplots(2,2,figsize=(10,6),sharex=True,sharey=True)
for ax,t,tl in zip(axs.flat,tasks,tlabels):
 for m in models: ax.plot(xlabs,[acc(m,l,t) for l in lengths],marker='o',lw=2,ms=5,color=colors[m],label=labels[m])
 ax.set_title(tl,loc='left',fontsize=10); ax.set_ylim(-3,103); ax.set_ylabel('Content accuracy (%)'); clean(ax)
 ax.set_xticks(range(3),xlabs)
fig.legend([plt.Line2D([0],[0],color=colors[m],marker='o',lw=2) for m in models],[labels[m] for m in models],loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,-.02))
fig.suptitle('Multi-fact accuracy falls with context length',x=.02,ha='left',fontsize=14,fontweight='bold'); fig.tight_layout(rect=(0,.06,1,.94)); save(fig,'fig1-accuracy-vs-length')
# b: headline comparison at 128K
fig,ax=plt.subplots(figsize=(8,3.6)); width=.23
for j,m in enumerate(models):
 vals=[acc(m,'long_128k',t) for t in ('single_retrieval','multi_retrieval')]
 xs=[0+j*width,1+j*width]
 ax.bar(xs,vals,width=width,color=colors[m],edgecolor=SURF,linewidth=1.3,label=labels[m])
 for x,v,t in zip(xs,vals,('single_retrieval','multi_retrieval')):
  rr=[r for r in rows if r['model']==m and r['length_label']=='long_128k' and r['task_type']==t]
  ax.text(x,v+2,f'{sum(int(r["correct"]) for r in rr)}/{len(rr)}',ha='center',fontsize=8,color=INK)
ax.set_xticks([.23,1.23],['Single fact','Four facts']); ax.set_ylabel('Content accuracy (%)'); ax.set_ylim(0,112); clean(ax)
ax.legend(frameon=False,ncol=3,loc='upper right'); ax.set_title('At 128K, four-fact retrieval is harder',loc='left',fontsize=13,fontweight='bold'); save(fig,'fig2-single-vs-four-fact-128k')
# c: prefill seconds by length
fig,ax=plt.subplots(figsize=(8,3.6))
for m in models:
 vals=[]
 for l in lengths:
  rr=[float(r['prefill_s']) for r in pref if r['model']==m and r['length_label']==l]
  vals.append(sum(rr)/len(rr))
 ax.plot(xlabs,vals,marker='o',lw=2.2,ms=5,color=colors[m],label=labels[m])
ax.set_ylabel('Document prefill time (s)'); clean(ax); ax.legend(frameon=False,ncol=3,loc='upper left'); ax.set_title('Prefill time by document length',loc='left',fontsize=13,fontweight='bold'); save(fig,'fig3-prefill-vs-length')
print('Wrote',', '.join(sorted(p.name for p in OUT.glob('fig*'))))
