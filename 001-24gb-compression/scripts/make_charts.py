"""Regenerate the article charts from DATA. Run from repo root:
   python3 001-24gb-compression/scripts/make_charts.py"""
import csv, json, statistics as st, collections, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for font_file in ("Anton-Regular.ttf", "IBMPlexMono-Regular.ttf"):
    font_manager.fontManager.addfont(pathlib.Path(__file__).resolve().parents[1] / "fonts" / font_file)

ROOT = pathlib.Path(__file__).resolve().parents[2]
_here = pathlib.Path(__file__).resolve()
D = _here.parents[1] / "DATA"
OUT = pathlib.Path(__file__).resolve().parents[1] / "CHARTS"
pc = json.load(open(D / "paired-comparison.json"))
tasks = {t["id"]: t["category"] for t in json.load(open(D / "tasks.json"))}
rows = list(csv.DictReader(open(D / "paired-runs.csv")))

C = {"nemotron": "#ba4e25", "qwen": "#2e65a0"}
NAME = {"nemotron": "Nemotron 3.5 Bolt 74B-A9B (2-bit)", "qwen": "Qwen3.8 27B (Q4_K_M)"}
GPU = {"rtx3090": "RTX 3090", "rtx5090": "RTX 5090"}
INK, MUTED, GRID, SURF = "#0a0a08", "#514e44", "#b8ad96", "#e7dfcc"
plt.rcParams.update({"font.family": "IBM Plex Mono", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "svg.fonttype": "path"})

def clean(ax, grid="x"):
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)

def save(fig, name):
    svg = OUT / name
    fig.savefig(svg, bbox_inches="tight")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    fig.savefig(OUT / name.replace(".svg", ".png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

# 1. Strict success with task-cluster bootstrap CI
cat_ci = {}
fig, ax = plt.subplots(figsize=(8, 3.2))
y = 0; labels = []; ys = []
for g in ("rtx3090", "rtx5090"):
    for m in ("nemotron", "qwen"):
        v = pc["models"][g][m]
        # model-level task-cluster CI is reported in RESULTS.md
        ci = {("rtx3090","nemotron"):(49.2,75.0),("rtx3090","qwen"):(61.7,85.0),("rtx5090","nemotron"):(45.8,72.5),("rtx5090","qwen"):(56.7,82.5)}[(g,m)]
        r = v["success_rate"] * 100
        ax.plot(ci, [y, y], color=C[m], lw=2, alpha=.45, solid_capstyle="round")
        ax.plot(r, y, "o", ms=9, color=C[m], mec=SURF, mew=2)
        ax.text(ci[1] + 1.2, y, f"{v['successes']}/120  ({r:.1f}%)", va="center", fontsize=9, color=INK)
        labels.append(f"{GPU[g]} · {'Nemotron' if m=='nemotron' else 'Qwen'}"); ys.append(y); y -= 1
    y -= 0.6
ax.set_yticks(ys, labels); ax.set_xlim(30, 100); ax.set_xlabel("Strict task success, % (line = 95% task-cluster bootstrap CI)")
ax.set_title("Qwen passed more strict tasks on both GPUs", loc="left", fontsize=13, fontfamily="Anton", color=INK, pad=10)
clean(ax); save(fig, "fig1-strict-success.svg")

# 2. Speed decomposition: decode rate, tokens generated, trial latency (three panels, one scale each)
agg = {}
for g in GPU:
    for m in C:
        v = [r for r in rows if r["gpu"] == g and r["model"] == m]
        agg[(g, m)] = dict(dec=st.mean(float(r["decode_tps"]) for r in v),
                           tok=st.mean(int(r["completion_tokens"]) for r in v),
                           med=pc["models"][g][m]["median_completion_s"], mean=pc["models"][g][m]["mean_completion_s"])
fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4))
panels = [("dec", "Decode rate (tok/s, mean)", "{:.1f}"), ("tok", "Tokens generated per trial (mean)", "{:.0f}"), ("med", "Full-trial latency (s, median)", "{:.2f}")]
for ax, (k, title, fmt) in zip(axs, panels):
    xs = []; xl = []
    for i, g in enumerate(GPU):
        for j, m in enumerate(C):
            x = i * 2.6 + j; val = agg[(g, m)][k]
            ax.bar(x, val, width=0.9, color=C[m], edgecolor=SURF, linewidth=2)
            ax.text(x, val, fmt.format(val), ha="center", va="bottom", fontsize=8.5, color=INK)
        xs.append(i * 2.6 + 0.5); xl.append(GPU[g])
    ax.set_xticks(xs, xl); ax.set_title(title, fontsize=10, loc="left", color=INK); clean(ax, "y"); ax.set_yticks([])
    ax.spines["bottom"].set_visible(True)
handles = [plt.Rectangle((0, 0), 1, 1, color=C[m]) for m in C]
fig.legend(handles, [NAME[m] for m in C], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.08))
fig.suptitle("Nemotron decodes ~2x faster, writes ~1.5x more tokens, median trial time ends up roughly even", x=0.01, ha="left", fontsize=13, fontfamily="Anton")
fig.tight_layout(); save(fig, "fig2-speed-decomposition.svg")

# 3. Category success, small multiples per GPU
cats = ["coding", "terminal_system", "tool_use", "structured_data", "multi_step"]
CN = {"coding": "Coding (12)", "terminal_system": "Terminal (8)", "tool_use": "Tool use (8)", "structured_data": "Structured data (6)", "multi_step": "Multi-step (6)"}
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
for ax, g in zip(axs, GPU):
    for i, c in enumerate(cats):
        for j, m in enumerate(C):
            v = pc["categories"][g][m][c]; r = v["success_rate"] * 100; yy = -i + (0.2 if j == 0 else -0.2)
            ax.barh(yy, r, height=0.38, color=C[m], edgecolor=SURF, linewidth=1.5)
            ax.text(r + 1.5, yy, f"{v['successes']}/{v['assignments']}", va="center", fontsize=8, color=MUTED)
    ax.set_yticks([-i for i in range(len(cats))], [CN[c] for c in cats]); ax.set_xlim(0, 112); ax.set_title(GPU[g], loc="left", fontsize=11)
    ax.set_xlabel("Strict success, %"); clean(ax)
fig.legend(handles, [NAME[m] for m in C], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.1))
fig.suptitle("Tool use is where the gap lives", x=0.01, ha="left", fontsize=13, fontfamily="Anton"); fig.tight_layout(); save(fig, "fig3-category-success.svg")

# 4. Failure classes, pooled across both GPUs (240 trials per model)
fails = collections.Counter((r["model"], r["failure_class"]) for r in rows if r["success"] == "0")
classes = sorted({k[1] for k in fails}, key=lambda c: -(fails[("nemotron", c)] + fails[("qwen", c)]))
fig, ax = plt.subplots(figsize=(8, 3.6))
for i, c in enumerate(classes):
    for j, m in enumerate(C):
        n = fails[(m, c)]; yy = -i + (0.2 if j == 0 else -0.2)
        ax.barh(yy, n, height=0.38, color=C[m], edgecolor=SURF, linewidth=1.5); ax.text(n + 0.4, yy, str(n), va="center", fontsize=8, color=MUTED)
ax.set_yticks([-i for i in range(len(classes))], [c.replace("_", " ") for c in classes]); ax.set_xlabel("Failed trials (both GPUs pooled, 240 trials per model)")
ax.set_title("Nemotron's extra failures: truncation and invalid JSON", loc="left", fontsize=13, fontfamily="Anton"); clean(ax)
ax.legend(handles, [NAME[m] for m in C], frameon=False, loc="lower right"); save(fig, "fig4-failure-classes.svg")
print("ok", sorted(p.name for p in OUT.iterdir()))
