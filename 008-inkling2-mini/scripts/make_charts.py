#!/usr/bin/env python3
"""Render the RTX 3090-only CUDA Recipes 008 graphics from selected result rows."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results.json"
OUT = ROOT / "CHARTS"
PAPER, INK, MUTED, GRID = "#e7dfcc", "#0a0a08", "#514e44", "#b8ad96"
BLUE, RUST = "#2e65a0", "#a3401c"
DEPTHS = [(0, "EMPTY"), (8192, "8K"), (131072, "128K"), (262144, "256K")]
SETTINGS = ["F16 / 2048/512\nn=3", "F16 / 2048/512\nn=3", "F16 / 256/128\nn=1", "Q8 / 64/32\nn=1"]


def text(fig, x, y, value, size=11, color=INK, *, display=False, **kwargs):
    return fig.text(x, y, value, fontsize=size, color=color,
                    fontfamily="Anton" if display else "IBM Plex Mono", **kwargs)


def rule(fig, y):
    fig.add_artist(Line2D([.055, .945], [y, y], transform=fig.transFigure, color=GRID, linewidth=.8))


def frame(height):
    fig = plt.figure(figsize=(12, height), facecolor=PAPER)
    text(fig, .055, .914, "MAJOR", 19, display=True)
    text(fig, .122, .914, "//", 19, RUST, display=True)
    text(fig, .153, .914, "MINOR", 19, display=True)
    text(fig, .945, .918, "CUDA RECIPES 008", 11, MUTED, ha="right")
    rule(fig, .876)
    rule(fig, .087)
    text(fig, .055, .041, "INKLING 2 MINI / Q4 / RTX 3090", 10, MUTED)
    text(fig, .945, .041, "MAJORMINOR.XYZ", 10, ha="right")
    return fig


def selected():
    rows = json.loads(RESULTS.read_text())["measurements"]
    return [r for r in rows if r["system"].startswith("rtx3090") and r["selection"] == "selected"]


def pick(rows, model, metric, depth=0):
    found = [r for r in rows if r["model"] == model and r["metric"] == metric and r["depth_tokens"] == depth]
    if len(found) != 1:
        raise SystemExit(f"expected one row for {model} {metric} {depth}, found {len(found)}")
    return found[0]


def hero(rows):
    tg = pick(rows, "base", "tg128")["mean_tok_s"]
    d128 = pick(rows, "base", "decode128", 131072)["mean_tok_s"]
    d256 = pick(rows, "base", "decode128", 262144)["mean_tok_s"]
    fig = frame(6.3)
    text(fig, .055, .657, "Inkling 2 Mini", 62, display=True)
    text(fig, .055, .495, "on one RTX 3090.", 62, display=True)
    text(fig, .660, .619, f"{tg:.1f}", 78, RUST, display=True)
    text(fig, .668, .535, "TOK/S GENERATION", 13)
    rule(fig, .397)
    text(fig, .055, .246, f"{d128:.1f} tok/s", 39, BLUE, display=True)
    text(fig, .055, .175, "128K FILLED / F16 / B256 UB128", 13)
    text(fig, .527, .246, f"{d256:.1f} tok/s", 39, RUST, display=True)
    text(fig, .527, .175, "256K FILLED / Q8 / B64 UB32", 13)
    fig.savefig(OUT / "overview.png", dpi=100)
    fig.savefig(OUT / "overview.svg", metadata={"Date": None})
    plt.close(fig)


def decode(rows):
    fig = frame(7.5)
    text(fig, .055, .765, "Decode with a filled context", 34, display=True)
    text(fig, .055, .715, "RTX 3090 / TOK/S / CACHE AND BATCH CHANGE WITH DEPTH", 11, MUTED)
    ax = fig.add_axes([.085, .285, .855, .385], facecolor=PAPER)
    ax.set_xlim(-.5, 3.5)
    ax.set_ylim(0, 70)
    ax.set_yticks([0, 20, 40, 60])
    ax.set_xticks(range(4), [label for _, label in DEPTHS])
    ax.grid(axis="y", color=GRID, linewidth=.7)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, colors=MUTED, labelsize=11, pad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for model, color, marker, offset, align in [("base", BLUE, "o", -.09, "right"), ("adq4", RUST, "D", .09, "left")]:
        points = [pick(rows, model, "decode128", depth) for depth, _ in DEPTHS]
        for i, row in enumerate(points):
            x, y = i + offset, row["mean_tok_s"]
            if row["repetitions"] > 1:
                ax.errorbar(x, y, yerr=row["sample_stddev_tok_s"], color=color, capsize=4, linewidth=1.6, zorder=2)
            ax.plot(x, y, marker=marker, color=color, markersize=8, markeredgecolor=PAPER, markeredgewidth=1.5, zorder=3)
            ax.annotate(f"{y:.2f}", (x, y), xytext=(-9 if align == "right" else 9, 0),
                        textcoords="offset points", ha=align, va="center", color=INK, fontsize=11)
    for i, label in enumerate(SETTINGS):
        ax.annotate(label, (i, 0), xytext=(0, -31), textcoords="offset points", ha="center", va="top",
                    annotation_clip=False, color=MUTED, fontsize=9, linespacing=1.3)
    fig.add_artist(Line2D([.055], [.128], marker="o", color=BLUE, markersize=8, linestyle="none", transform=fig.transFigure))
    text(fig, .067, .120, "Base UD-Q4_K_M", 10.5)
    fig.add_artist(Line2D([.235], [.128], marker="D", color=RUST, markersize=7, linestyle="none", transform=fig.transFigure))
    text(fig, .247, .120, "Uncensored AD-Q4_K", 10.5)
    text(fig, .945, .120, "128K and 256K: one run, separate 3090 host", 10, MUTED, ha="right")
    fig.savefig(OUT / "decode-depth.png", dpi=150)
    fig.savefig(OUT / "decode-depth.svg", metadata={"Date": None})
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("Anton-Regular.ttf", "IBMPlexMono-Regular.ttf"):
        font_manager.fontManager.addfont(ROOT / "fonts" / name)
    plt.rcParams.update({"font.family": "IBM Plex Mono", "font.size": 11, "svg.fonttype": "path", "svg.hashsalt": "cuda-recipes-008-3090-v1"})
    rows = selected()
    hero(rows)
    decode(rows)
    figures = {
        "overview": [pick(rows, "base", "tg128"), pick(rows, "base", "decode128", 131072), pick(rows, "base", "decode128", 262144)],
        "decode-depth": [pick(rows, model, "decode128", depth) for model in ("base", "adq4") for depth, _ in DEPTHS],
    }
    export = {name: {"measurement_ids": [r["id"] for r in used], "values": [{k: r[k] for k in ("id", "mean_tok_s", "sample_stddev_tok_s", "samples_tok_s")} for r in used]} for name, used in figures.items()}
    (OUT / "figure-data.json").write_text(json.dumps(export, indent=2) + "\n")
    for path in OUT.glob("*.svg"):
        path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    print("Rendered RTX 3090 overview and depth graphics.")


if __name__ == "__main__":
    main()
