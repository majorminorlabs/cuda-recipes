#!/usr/bin/env python3
"""Build scratchpad figures from saved baseline and scratchpad CSVs."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'DATA'; OUT=ROOT/'CHARTS'
OUT.mkdir(exist_ok=True)

def read(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))

scratch=read(DATA/'scratchpad'/'answer-results.csv')
base=read(DATA/'answer-results.csv')+read(DATA/'code'/'answer-results.csv')
models=['qwen36_35b_a3b','nemotron','qwen38_27b']
labels={'qwen36_35b_a3b':'Qwen3.6 35B-A3B','nemotron':'Nemotron 3.5 Bolt','qwen38_27b':'Qwen3.8 27B'}
colors={'qwen36_35b_a3b':'#7651a8','nemotron':'#ba4e25','qwen38_27b':'#2e65a0'}
lengths=['control','long_64k','long_128k']; xlabs=['Control','64K','128K']
INK,MUTED,GRID,SURF='#0a0a08','#514e44','#b8ad96','#e7dfcc'
plt.rcParams.update({'font.family':'DejaVu Sans Mono','font.size':8,'axes.edgecolor':GRID,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,'text.color':INK,'figure.facecolor':SURF,'axes.facecolor':SURF,'svg.fonttype':'none'})

def clean(ax,axis='y'):
    for s in ('top','right','left'): ax.spines[s].set_visible(False)
    ax.grid(axis=axis,color=GRID,lw=.7); ax.set_axisbelow(True); ax.tick_params(length=0)

def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=200,bbox_inches='tight',facecolor=SURF)
    plt.close(fig)

def wilson(x,n,z=1.959963984540054):
    if n==0: return 0,0
    p=x/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,mid-half),min(1,mid+half)

def base_count(model,length):
    rows=[r for r in base if r['model']==model and r['doc_id']==length and r['task_type']=='aggregation']
    return sum(int(r['correct']) for r in rows),len(rows)

def new_count(model,length):
    rows=[r for r in scratch if r['model']==model and r['length_label']==length]
    return sum(int(r['final_count_correct']) for r in rows),len(rows)

# a) baseline vs scratchpad final-count accuracy, pooled arms, Wilson intervals.
fig,axs=plt.subplots(1,3,figsize=(11,3.7),sharey=True)
x=np.arange(3); width=.32
for ax,m in zip(axs,models):
    vals=[]; lows=[]; highs=[]
    for series in (base_count,new_count):
        cs=[series(m,l)[0] for l in lengths]; ns=[series(m,l)[1] for l in lengths]
        lohi=[wilson(c,n) for c,n in zip(cs,ns)]
        vals.append(np.array(cs,float))
        lows.append(np.array([c-n*lo for c,n,(lo,hi) in zip(cs,ns,lohi)]))
        highs.append(np.array([n*hi-c for c,n,(lo,hi) in zip(cs,ns,lohi)]))
    ax.bar(x-width/2,vals[0],width,color='#b8ad96',edgecolor=INK,linewidth=.7,hatch='//',label='003 baseline')
    ax.bar(x+width/2,vals[1],width,color=colors[m],edgecolor=SURF,linewidth=.8,label='Scratchpad')
    ax.errorbar(x-width/2,vals[0],yerr=[lows[0],highs[0]],fmt='none',ecolor=INK,capsize=2,lw=1)
    ax.errorbar(x+width/2,vals[1],yerr=[lows[1],highs[1]],fmt='none',ecolor=INK,capsize=2,lw=1)
    for j,l in enumerate(lengths):
        for off,fn in [(-width/2,base_count),(width/2,new_count)]:
            c,n=fn(m,l); ax.text(j+off,c+.5,f'{c}/{n}',ha='center',va='bottom',fontsize=6,color=INK)
    ax.set_title(labels[m],loc='left',fontsize=9,fontweight='bold')
    ax.set_xticks(x,xlabs); ax.set_ylim(0,30); ax.set_yticks(np.arange(0,31,5)); clean(ax)
axs[0].set_ylabel('Final count correct (out of 30)')
fig.legend(handles=[Patch(facecolor='#b8ad96',edgecolor=INK,hatch='//',label='003 baseline'),Patch(facecolor=colors[models[0]],edgecolor=SURF,label='Scratchpad; model color')],frameon=False,ncol=2,loc='upper center',bbox_to_anchor=(.5,1.01))
fig.suptitle('Scratchpad count accuracy vs. 003 aggregation baseline',x=.01,y=1.12,ha='left',fontsize=12,fontweight='bold')
fig.tight_layout(rect=(0,0,1,.90)); save(fig,'scratchpad-final-count-baseline')

# b) failure-class counts per model, with prose/code adjacent at every length.
fails=['correct','decoy_included','extra_item','missed_items','no_list','truncated','invalid_json','miscount_of_list']
f_labels=['Correct','Decoy','Extra item','Missed item','No tally','Truncated','Invalid JSON','Miscount']
f_colors=['#2e7b64','#ba4e25','#d5a53c','#7651a8','#2e65a0','#a83f45','#252522','#82919b']
fig,axs=plt.subplots(1,3,figsize=(12,4),sharey=True)
for ax,m in zip(axs,models):
    x=np.arange(3); w=.30
    for j,(arm,off,hatch) in enumerate([('prose',-w/2,''),('code',w/2,'//')]):
        bottoms=np.zeros(3)
        for fc,fl,col in zip(fails,f_labels,f_colors):
            heights=np.array([sum(r['model']==m and r['arm']==arm and r['length_label']==l and r['failure_class']==fc for r in scratch) for l in lengths])
            ax.bar(x+off,heights,w,bottom=bottoms,color=col,edgecolor=SURF,linewidth=.5,hatch=hatch,label=fl if j==0 else None)
            bottoms+=heights
        for xi in x: ax.text(xi+off,-.65,'P' if arm=='prose' else 'C',ha='center',va='top',fontsize=7,color=MUTED)
    ax.set_title(labels[m],loc='left',fontsize=9,fontweight='bold')
    ax.set_xticks(x,xlabs); ax.set_ylim(-1.5,16); ax.set_yticks([0,5,10,15]); clean(ax)
axs[0].set_ylabel('Answers (n=15 per arm cell)')
fig.legend(handles=[plt.Rectangle((0,0),1,1,color=c) for c in f_colors],labels=f_labels,frameon=False,ncol=4,loc='upper center',bbox_to_anchor=(.5,1.12))
fig.suptitle('Failure classes by model, length and arm',x=.01,ha='left',fontsize=12,fontweight='bold')
fig.text(.5,.01,'P = prose   C = code',ha='center',color=MUTED,fontsize=8)
fig.tight_layout(rect=(0,.04,1,.93)); save(fig,'scratchpad-failure-classes')

# c) planted-item recall by arm and length, denominator from score rows.
fig,axs=plt.subplots(1,3,figsize=(11,3.7),sharey=True)
x=np.arange(3)
for ax,m in zip(axs,models):
    series={}
    for arm in ('prose','code'):
        ys=[]
        for le in lengths:
            rr=[r for r in scratch if r['model']==m and r['arm']==arm and r['length_label']==le]
            f=sum(int(r['matched_planted']) for r in rr); d=f+sum(int(r['missed_planted']) for r in rr)
            ys.append(100*f/d if d else 0)
        series[arm]=ys
    for arm,ls,marker,label in [('prose','-','o','Prose'),('code','--','s','Code')]:
        ys=series[arm]
        ax.plot(x,ys,ls=ls,marker=marker,lw=2,ms=5,color=colors[m],label=label)
        for i,(xi,y) in enumerate(zip(x,ys)):
            other=series['code' if arm=='prose' else 'prose'][i]
            if abs(y-other)<18:
                offset=(8 if y>=other else -8) if arm=='prose' else (8 if y>other else -8)
            else:
                offset=7 if arm=='prose' else -7
            ax.text(xi,y+offset,f'{y:.0f}%',ha='center',va='center',fontsize=7,color=INK)
    ax.set_title(labels[m],loc='left',fontsize=9,fontweight='bold')
    ax.set_xticks(x,xlabs); ax.set_ylim(0,110); ax.set_yticks(np.arange(0,101,20)); clean(ax)
axs[0].set_ylabel('Planted items found (%)')
fig.legend([plt.Line2D([0],[0],color=colors[models[0]],lw=2,marker='o'),plt.Line2D([0],[0],color=colors[models[0]],lw=2,ls='--',marker='s')],['Prose','Code'],frameon=False,ncol=2,loc='upper center',bbox_to_anchor=(.5,1.08))
fig.suptitle('Planted-item recall by arm and context length',x=.01,ha='left',fontsize=12,fontweight='bold')
fig.tight_layout(rect=(0,0,1,.96)); save(fig,'scratchpad-planted-recall')
print('Wrote three scratchpad PNG charts')
