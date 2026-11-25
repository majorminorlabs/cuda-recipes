#!/usr/bin/env python3
"""Render CUDA Recipes 009 charts in the Major Minor research palette."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "CHARTS"
DATA = json.loads((OUT / "figure-data.json").read_text())
PAPER, INK, MUTED, GRID = "#e7dfcc", "#0a0a08", "#514e44", "#b8ad96"
BLUE, RUST = "#2e65a0", "#a3401c"
COLORS = {"paper": PAPER, "ink": INK, "muted": MUTED, "grid": GRID, "blue": BLUE, "rust": RUST}


def frame(height, footer="TERNARY BONSAI 2.5 / QWEN3.8 / RTX 3090"):
    fig = plt.figure(figsize=(12, height), facecolor=PAPER)
    fig.text(.055, .928, "MAJOR", fontsize=19, color=INK, fontfamily="Anton")
    fig.text(.122, .928, "//", fontsize=19, color=RUST, fontfamily="Anton")
    fig.text(.153, .928, "MINOR", fontsize=19, color=INK, fontfamily="Anton")
    fig.text(.945, .932, "CUDA RECIPES 009", fontsize=10, color=MUTED, ha="right", fontfamily="IBM Plex Mono")
    fig.add_artist(Line2D([.055, .945], [.888, .888], transform=fig.transFigure, color=GRID, linewidth=.8))
    fig.add_artist(Line2D([.055, .945], [.075, .075], transform=fig.transFigure, color=GRID, linewidth=.8))
    fig.text(.055, .035, footer, fontsize=9, color=MUTED, fontfamily="IBM Plex Mono")
    fig.text(.945, .035, "MAJORMINOR.XYZ", fontsize=9, color=MUTED, ha="right", fontfamily="IBM Plex Mono")
    return fig


def style_axis(ax, grid="x"):
    ax.set_facecolor(PAPER)
    ax.grid(axis=grid, color=GRID, linewidth=.7)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, colors=MUTED, labelsize=9, pad=7)
    for spine in ax.spines.values(): spine.set_visible(False)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=150, facecolor=PAPER)
    svg=OUT / f"{name}.svg"
    fig.savefig(svg, facecolor=PAPER, metadata={"Date": None})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)


def overview():
    fig = frame(6.6)
    fig.text(.055, .800, "More decode speed.", fontsize=34, color=INK, fontfamily="Anton")
    fig.text(.055, .710, "Fewer strict passes.", fontsize=34, color=INK, fontfamily="Anton")
    fig.text(.055, .650, "RTX 3090 / quality suite and fresh F16 benchmark / distinct measurements", fontsize=10, color=MUTED, fontfamily="IBM Plex Mono")
    q=DATA["quality"]["arms"]
    ax=fig.add_axes([.10,.275,.35,.31]); style_axis(ax)
    vals=[sum(a["successes"])/120*100 for a in q]
    labels=["QWEN · 001", "PTQ1 PLAIN", "PTQ1 MTP"]
    colors=[BLUE,RUST,INK]
    y=list(range(3))[::-1]
    ax.barh(y,vals,color=colors,height=.55)
    ax.set_yticks(y,labels); ax.set_xlim(0,115); ax.set_xticks([0,25,50,75,100]); ax.set_xlabel("STRICT TASK SUCCESS (%)",fontsize=8,color=MUTED,labelpad=9)
    for yi,v,a in zip(y,vals,q): ax.text(v+2,yi,a["strict_total"],va="center",fontsize=10,color=INK)
    fig.text(.10,.605,"QUALITY / FROZEN 001 SUITE",fontsize=11,color=INK,fontfamily="IBM Plex Mono")
    rows=DATA["speed"]["rows"][:3]
    ax2=fig.add_axes([.58,.275,.34,.31]); style_axis(ax2)
    vals=[r["tg128"] for r in rows]; y=list(range(3))[::-1]
    ax2.barh(y,vals,color=[COLORS[r["color"]] for r in rows],height=.55)
    ax2.set_yticks(y,["QWEN · PRISM", "PTQ1 PLAIN", "MTP FILE · OFF"]); ax2.set_xlim(0,115); ax2.set_xticks([0,25,50,75,100]); ax2.set_xlabel("FRESH TG128 DECODE (TOK/S)",fontsize=8,color=MUTED,labelpad=9)
    for yi,r in zip(y,rows): ax2.text(r["tg128"]+2,yi,str(r["tg128"]),va="center",fontsize=9,color=INK)
    fig.text(.58,.605,"SPEED / PRISM BUILD / F16 K/V",fontsize=11,color=INK,fontfamily="IBM Plex Mono")
    fig.text(.10,.175,"QWEN BASELINE: 89/120  ·  BONSAI PLAIN: 81/120  ·  BONSAI MTP: 79/120",fontsize=10,color=MUTED,fontfamily="IBM Plex Mono")
    fig.text(.10,.125,"Bonsai PTQ1 plain: 94.536232 tok/s tg128; Qwen on same build: 45.972666 tok/s.",fontsize=9,color=MUTED,fontfamily="IBM Plex Mono")
    save(fig,"overview")


def quality():
    fig=frame(8.2,footer="STRICT SUCCESSES / TRIALS BY CATEGORY / QWEN ARM REUSED FROM 001")
    fig.text(.055,.82,"The gap is concentrated in tool use and multi-step work.",fontsize=25,color=INK,fontfamily="Anton")
    fig.text(.055,.77,"COUNTS SHOWN AT BAR ENDS / BARS NORMALIZED WITHIN CATEGORY",fontsize=9,color=MUTED,fontfamily="IBM Plex Mono")
    q=DATA["quality"]; arms=q["arms"]; cats=q["categories"]
    ax=fig.add_axes([.25,.245,.58,.455]); style_axis(ax)
    base=list(range(len(cats)))[::-1]; offsets=[.22,0,-.22]
    for arm,offset in zip(arms,offsets):
        vals=[s/n*100 for s,n in zip(arm["successes"],arm["assignments"])]
        ys=[b+offset for b in base]
        ax.barh(ys,vals,height=.18,color=COLORS[arm["color"]],label=arm["label"])
        for yy,v,s,n in zip(ys,vals,arm["successes"],arm["assignments"]):
            ax.text(v+1.5,yy,f"{s}/{n}",va="center",fontsize=8,color=INK)
    ax.set_yticks(base,cats); ax.set_xlim(0,125); ax.set_xticks([0,25,50,75,100]); ax.set_xlabel("STRICT SUCCESS (%)",fontsize=9,color=MUTED,labelpad=8)
    handles=[Patch(facecolor=COLORS[a["color"]],label=f'{a["label"]} · {a["strict_total"]}') for a in arms]
    fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.53,.105),ncol=3,frameon=False,fontsize=8)
    save(fig,"quality-categories")


def speed():
    fig=frame(8.0,footer="LLAMA-BENCH / 3 REPETITIONS / F16 K/V / QWEN ROW FRESH ON EACH BUILD")
    fig.text(.055,.82,"Decode speed moves most.",fontsize=28,color=INK,fontfamily="Anton")
    fig.text(.055,.77,"MTP-head benchmark ran with drafting disabled; it is not the MTP-on server result.",fontsize=9,color=MUTED,fontfamily="IBM Plex Mono")
    rows=DATA["speed"]["rows"]
    labels=[r["label"] for r in rows]; colors=[COLORS[r["color"]] for r in rows]; y=list(range(len(rows)))[::-1]
    ax1=fig.add_axes([.25,.48,.60,.22]); style_axis(ax1)
    ax1.barh(y,[r["pp512"] for r in rows],color=colors,height=.56)
    ax1.set_yticks(y,labels); ax1.set_xlim(0,1900); ax1.set_xticks([0,500,1000,1500]); ax1.set_xlabel("PREFILL 512 (TOK/S)",fontsize=8,color=MUTED,labelpad=6)
    for yy,r in zip(y,rows): ax1.text(r["pp512"]+18,yy,str(r["pp512"]),va="center",fontsize=8,color=INK)
    ax2=fig.add_axes([.25,.16,.60,.22]); style_axis(ax2)
    ax2.barh(y,[r["tg128"] for r in rows],color=colors,height=.56)
    ax2.set_yticks(y,labels); ax2.set_xlim(0,120); ax2.set_xticks([0,30,60,90,120]); ax2.set_xlabel("GENERATION 128 (TOK/S)",fontsize=8,color=MUTED,labelpad=6)
    for yy,r in zip(y,rows): ax2.text(r["tg128"]+1.5,yy,str(r["tg128"]),va="center",fontsize=8,color=INK)
    save(fig,"speed-builds")


def filled():
    fig=frame(7.7,footer="SYNTHETIC FILL / DECODE ONLY / SETTINGS CHANGE WITH DEPTH")
    fig.text(.055,.82,"Filled-context decode",fontsize=30,color=INK,fontfamily="Anton")
    fig.text(.055,.765,"Bars are grouped by depth; they are not connected across different cache and batch settings.",fontsize=9,color=MUTED,fontfamily="IBM Plex Mono")
    fc=DATA["filled_context"]; models=fc["models"]; x=list(range(3)); width=.18
    ax=fig.add_axes([.10,.27,.80,.40]); style_axis(ax,grid="y")
    offsets=[-.27,-.09,.09,.27]
    for model,offset in zip(models,offsets):
        vals=model["decode_tok_s"]
        for i,val in enumerate(vals):
            xpos=x[i]+offset
            if val is None:
                ax.plot([xpos],[0],marker="x",markersize=10,markeredgewidth=2,color=COLORS[model["color"]])
                ax.annotate("OOM",(xpos,.5),xytext=(0,7),textcoords="offset points",ha="center",fontsize=8,color=COLORS[model["color"]])
            else:
                ax.bar(xpos,val,width,color=COLORS[model["color"]],zorder=3)
                ax.text(xpos,val+1.2,str(val),ha="center",va="bottom",fontsize=7,color=INK,rotation=90)
    ax.set_ylim(0,90); ax.set_yticks([0,20,40,60,80]); ax.set_xticks(x,fc["depths"]); ax.set_ylabel("DECODE (TOK/S)",fontsize=8,color=MUTED,labelpad=8)
    for i,setting in enumerate(fc["settings"]): ax.text(i,-.12,setting,ha="center",va="top",transform=ax.get_xaxis_transform(),fontsize=8,color=MUTED)
    handles=[Patch(facecolor=COLORS[m["color"]],label=m["label"]) for m in models]
    fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.50,.105),ncol=2,frameon=False,fontsize=8)
    save(fig,"filled-context")


def mtp():
    fig=frame(6.6,footer="THREE FIXED PROMPTS / SERVER MICROCOMPARISON / SAME MTP-HEAD FILE")
    fig.text(.055,.81,"What the MTP head changed",fontsize=30,color=INK,fontfamily="Anton")
    fig.text(.055,.755,"MTP-on used CUDA p_min 0.1; 206 of 506 draft tokens were accepted.",fontsize=10,color=MUTED,fontfamily="IBM Plex Mono")
    modes=DATA["mtp_server"]["modes"]; y=[1,0]
    ax1=fig.add_axes([.18,.40,.68,.24]); style_axis(ax1)
    vals=[m["generation_tok_s"] for m in modes]
    ax1.barh(y,vals,color=[BLUE,RUST],height=.48)
    ax1.set_yticks(y,["DRAFTING OFF","MTP ON · P_MIN 0.1"]); ax1.set_xlim(0,210); ax1.set_xticks([0,50,100,150,200]); ax1.set_xlabel("GENERATION (TOK/S)",fontsize=8,color=MUTED,labelpad=6)
    for yy,m in zip(y,modes): ax1.text(m["generation_tok_s"]+3,yy,str(m["generation_tok_s"]),va="center",fontsize=9,color=INK)
    fig.text(.18,.285,"Prompt throughput: off 181.05846969006166 tok/s  ·  on 159.00202748181158 tok/s",fontsize=8.5,color=MUTED,fontfamily="IBM Plex Mono")
    fig.text(.18,.235,"Peak VRAM: off 6558 MiB  ·  on 7330 MiB  ·  384 vs 379 output tokens",fontsize=8.5,color=MUTED,fontfamily="IBM Plex Mono")
    save(fig,"mtp-check")


def main():
    for name in ("Anton-Regular.ttf","IBMPlexMono-Regular.ttf"):
        font_manager.fontManager.addfont(ROOT/"fonts"/name)
    plt.rcParams.update({"font.family":"IBM Plex Mono","font.size":9,"text.color":INK,"axes.labelcolor":MUTED,"xtick.color":MUTED,"ytick.color":MUTED,"svg.fonttype":"path","svg.hashsalt":"cuda-recipes-009-brand-v1"})
    OUT.mkdir(parents=True,exist_ok=True)
    overview(); quality(); speed(); filled(); mtp()

if __name__ == "__main__": main()
