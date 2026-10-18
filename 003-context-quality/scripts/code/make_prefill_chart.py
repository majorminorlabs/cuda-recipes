#!/usr/bin/env python3
"""Render fig6 from published code prefill measurements with separated Control labels."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "CHARTS"
MODELS = ["qwen36_35b_a3b", "nemotron", "qwen38_27b"]
LABELS = ["Qwen3.6 35B-A3B", "Nemotron 3.5 Bolt", "Qwen3.8 27B"]
COLORS = ["#7651a8", "#ba4e25", "#2e65a0"]
LENGTHS = ["control", "long_64k", "long_128k"]
plt.rcParams.update({"font.family": "DejaVu Sans Mono", "font.size": 9,
                     "text.color": "#514e44", "axes.labelcolor": "#514e44",
                     "xtick.color": "#514e44", "ytick.color": "#514e44",
                     "axes.edgecolor": "#b8ad96", "figure.facecolor": "#e7dfcc",
                     "axes.facecolor": "#e7dfcc", "svg.fonttype": "none"})
with (ROOT / "DATA/code/prefill-results.csv").open(newline="") as source:
    rows = list(csv.DictReader(source))
fig, ax = plt.subplots(figsize=(7.2, 4.6))
for model, label, color, control_offset in zip(MODELS, LABELS, COLORS, [(-12, 13), (0, 30), (18, 14)]):
    values = []
    for length in LENGTHS:
        samples = [float(row["prefill_s"]) for row in rows if row["model"] == model and row["length_label"] == length]
        values.append(sum(samples) / len(samples))
    ax.plot(range(3), values, marker="o", linewidth=2, markersize=5, color=color, label=label)
    for index, value in enumerate(values):
        ax.annotate(f"{value:.1f}", (index, value), xytext=control_offset if index == 0 else (0, 6),
                    textcoords="offset points", ha="center", va="bottom", color=color, fontsize=8)
ax.set_xticks(range(3), ["Control", "64K", "128K"])
ax.set_ylabel("Prefill time (seconds)")
ax.set_ylim(0, 210)
ax.grid(axis="y", color="#b8ad96", linewidth=.7)
ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False)
fig.suptitle("CODE ARM · PREFILL TIME", x=.02, ha="left", fontweight="bold", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, .94))
OUT.mkdir(exist_ok=True)
for extension in ["svg", "png"]:
    fig.savefig(OUT / f"fig6-code-prefill-vs-length.{extension}", dpi=180, bbox_inches="tight", metadata={"Date": None} if extension == "svg" else {})
plt.close(fig)
