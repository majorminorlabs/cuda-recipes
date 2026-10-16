#!/usr/bin/env python3
"""Regenerate the study SVG charts from config and CSV data (stdlib only)."""
import csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'DATA'; OUT=ROOT/'CHARTS';OUT.mkdir(exist_ok=True)
cfg=json.loads((D/'study-config.json').read_text()); loads=list(csv.DictReader((D/'load-results.csv').open()));bench=list(csv.DictReader((D/'bench-results.csv').open()))
COL={'nemotron':'#ba4e25','qwen':'#2e65a0'}; NAME={'nemotron':'Nemotron','qwen':'Qwen'}
BG='#e7dfcc';INK='#0a0a08';MUTED='#514e44';GRID='#b8ad96'
VRAM=int(re.search(r'(\d+)GB',cfg['gpu']).group(1))*1024
W,H=900,480; L,R,T,B=90,45,72,108; PW,PH=W-L-R,H-T-B
def esc(s):return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def chart(name,title,xlabel,ylabel,xmax,ymax,xticks,yticks,series,capacity=None,note=None):
 def X(x):return L+float(x)/xmax*PW
 def Y(y):return T+PH-float(y)/ymax*PH
 a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="100%" height="100%" fill="{BG}"/>',f'<text x="{L}" y="36" font-family="sans-serif" font-size="21" font-weight="700" fill="{INK}">{esc(title)}</text>']
 if note:a.append(f'<text x="{L}" y="58" font-family="monospace" font-size="11" fill="{MUTED}">{esc(note)}</text>')
 for y,label in yticks:
  a += [f'<line x1="{L}" y1="{Y(y):.1f}" x2="{W-R}" y2="{Y(y):.1f}" stroke="{GRID}"/>',f'<text x="{L-12}" y="{Y(y)+4:.1f}" text-anchor="end" font-family="monospace" font-size="12" fill="{MUTED}">{esc(label)}</text>']
 for x,label in xticks:
  a += [f'<line x1="{X(x):.1f}" y1="{T}" x2="{X(x):.1f}" y2="{T+PH}" stroke="{GRID}" opacity=".45"/>',f'<text x="{X(x):.1f}" y="{T+PH+23}" text-anchor="middle" font-family="monospace" font-size="12" fill="{MUTED}">{esc(label)}</text>']
 if capacity is not None:
  y=Y(capacity);a += [f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{INK}" stroke-width="2" stroke-dasharray="8 5"/>',f'<text x="{W-R-2}" y="{y-7:.1f}" text-anchor="end" font-family="monospace" font-size="12" fill="{INK}">{capacity:,} MiB card</text>']
 for si,s in enumerate(series):
  color=s['color']; pts=s['points']
  if s.get('connect',True) and len(pts)>1:a.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(f"{X(x):.1f},{Y(y):.1f}" for x,y,_ in pts)}"/>')
  for x,y,label in pts:
   a.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="6" fill="{BG}" stroke="{color}" stroke-width="3"/>')
   if label:
    dx=(s.get('label_dx',0) if abs(x-64)<0.01 else (8 if abs(x)<0.01 else 0)); anchor=(s.get('label_anchor','middle') if abs(x-64)<0.01 else ('start' if abs(x)<0.01 else 'middle'))
    label_y=Y(y)-16 if s.get('label_side')=='above' else (Y(y)+24 if s.get('label_side')=='below' else Y(y)-11)
    a.append(f'<text x="{X(x)+dx:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" font-family="monospace" font-size="11" fill="{color}">{esc(label)}</text>')
  if s.get('range'):
   lo,hi=s['range'];x=X(0 if s.get('range_x') is None else s['range_x']);a.append(f'<line x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" y2="{Y(hi):.1f}" stroke="{color}" stroke-width="9" stroke-linecap="round" opacity=".65"/>')
   for v in (lo,hi):a.append(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="4" fill="{color}"/>')
  label_width=len(s['name'])*7.2; lx=L+si*PW/2+PW/4-(28+8+label_width)/2; a += [f'<line x1="{lx:.1f}" y1="{H-14}" x2="{lx+28:.1f}" y2="{H-14}" stroke="{color}" stroke-width="4"/>',f'<text x="{lx+36:.1f}" y="{H-9}" font-family="monospace" font-size="12" fill="{INK}">{esc(s["name"])}</text>']
 a += [f'<text x="{L+PW/2}" y="{H-42}" text-anchor="middle" font-family="monospace" font-size="13" fill="{MUTED}">{esc(xlabel)}</text>',f'<text transform="translate(22 {T+PH/2}) rotate(-90)" text-anchor="middle" font-family="monospace" font-size="13" fill="{MUTED}">{esc(ylabel)}</text>','</svg>']
 (OUT/(name+'.svg')).write_text('\n'.join(a)+'\n')
def pts_for(metric,model,nonzero_label=False):
 rows=sorted((r for r in bench if r['model']==model),key=lambda r:int(r['depth_tokens']));return [(int(r['depth_tokens'])/1024,float(r[metric]),f"{float(r[metric]):.1f}" if nonzero_label and int(r['depth_tokens'])>0 else '') for r in rows if int(r['depth_tokens'])>0]
# VRAM by context, successful load attempts, native or searched ceilings marked.
ss=[]
for m in cfg['models']:
 rr=sorted((r for r in loads if r['model']==m and r['loaded_full_gpu']=='1'),key=lambda r:int(r['ctx_size']))
 c=next(int(r['ctx_size']) for r in rr if r['is_ceiling']=='1');ss.append({'name':NAME[m],'color':COL[m],'points':[(int(r['ctx_size'])/1024,int(r['peak_vram_load_mib']),f"ceiling {c//1024}K" if int(r['ctx_size'])==c else '') for r in rr]})
chart('fig1-peak-vram-context','Peak VRAM rises with loaded context','Loaded context window (K tokens)','Peak VRAM (MiB)',280,26000,[(0,'0'),(64,'64K'),(128,'128K'),(192,'192K'),(256,'256K')],[(0,'0'),(6000,'6K'),(12000,'12K'),(18000,'18K'),(24000,'24K')],ss,VRAM)
for metric,name,title,ylabel,ymax,step in [('decode_tps','fig2-decode-fill-depth','Decode speed falls with fill depth','Decode (tok/s)',100,20),('prompt_tps','fig3-prompt-fill-depth','Prompt processing crosses over at deeper fill','Prompt processing (tok/s)',1400,200)]:
 series=[]
 for m in cfg['models']:
  z=[float(r[metric]) for r in bench if r['model']==m and int(r['depth_tokens'])==0];series.append({'name':'Nemotron Bolt 2-bit' if m=='nemotron' else 'Qwen3.8 27B Q4_K_M','color':COL[m],'points':[(0,sum(z)/len(z),f'{min(z):.1f}–{max(z):.1f}')]+pts_for(metric,m,True),'connect':True,'range':(min(z),max(z)),'range_x':1 if m=='nemotron' else 5,'label_dx':-18 if m=='nemotron' else 18,'label_anchor':'end' if m=='nemotron' else 'start','label_side':'above' if m=='nemotron' else 'below'})
 # Use a slight visual x offset for nonzero depth-zero range to keep both visible.
 chart(name,title,'Synthetic fill depth (K tokens)',ylabel,260,ymax,[(0,'0'),(64,'64K'),(128,'128K'),(192,'192K'),(256,'256K')],[(v,f'{v:,}') for v in range(0,ymax+1,step)],series,note='Depth 0 marker shows the three-run min–max; deeper points are single runs.')
# For speed chart baseline ranges use near-zero x positions; add labels in legend.
ss=[]
for m in cfg['models']:
 rr=sorted((r for r in loads if r['model']==m and r['loaded_full_gpu']=='1'),key=lambda r:int(r['ctx_size']))
 ss.append({'name':NAME[m],'color':COL[m],'points':[(int(r['ctx_size'])/1024,float(r['kv_buffer_mib']),'') for r in rr]})
chart('fig4-kv-cache-context','Qwen uses 8× the KV cache per token','Loaded context window (K tokens)','KV cache (MiB)',280,8000,[(0,'0'),(64,'64K'),(128,'128K'),(192,'192K'),(256,'256K')],[(0,'0'),(2000,'2K'),(4000,'4K'),(6000,'6K'),(8000,'8K')],ss)
print('\n'.join(str(p.relative_to(ROOT)) for p in sorted(OUT.glob('fig*.svg'))))
