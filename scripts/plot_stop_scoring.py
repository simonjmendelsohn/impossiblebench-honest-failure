"""Figure: how scoring a "stop" changes Gemini 3.1 Pro's ImpossibleBench cheat rate.

Gemini 3.1 Pro preview, ImpossibleBench's minimal retry loop, prompt D, both impossible splits (202 tasks per bar):
  1. paper's exact prompt ending (arm D_paper), normal scorer
  2. our prompt ending (arm D), normal scorer
  3. our ending, patched scorer: an exit before check() finishes counts as a failure (arm D_patched)
  4. our ending, stop option named in the prompt (arm D_abort)
Each bar splits the benchmark's cheat rate (= pass rate) into passes the judge labels `stop_via_exit` and other passes.
The tick marks the central estimate of runs that actually gamed the tests (scripts/pro_range.py).

With --simple, only bars 1 and 4 and no estimate tick (the version used in the write-up's summary post).

  python scripts/plot_stop_scoring.py [results] [--simple]   -> figures/stop_scoring.png / stop_scoring_simple.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib import patheffects as pe
from matplotlib.patches import FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parent.parent
SIMPLE = "--simple" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
src = Path(args[0]) if args else ROOT / "results"
out = ROOT / "figures" / ("stop_scoring_simple.png" if SIMPLE else "stop_scoring.png")

# Central estimates of gaming from scripts/pro_range.py (per split, summed over both splits, out of 202)
CENTRAL = {} if SIMPLE else {"D_paper": (26.6 + 21.9) / 202, "D": (19.6 + 20.4) / 202}

r = pd.read_csv(src / "runs_labeled.csv")
r = r[(r.model == "gemini-3.1-pro-preview") & (r.harness == "inspect_minimal") & r.split.isin(["oneoff", "conflicting"])]
ROWS = [
    ("D_paper", "No stop option offered", "the paper's exact prompt"),
    ("D_abort", "A stop option named in the prompt", "“submit [flag_for_human_intervention]”"),
] if SIMPLE else [
    ("D_paper", "The paper's exact prompt", "normal scorer"),
    ("D", "One sentence of boilerplate changed", "normal scorer"),
    ("D_patched", "exit(0) no longer counts as a pass", "patched scorer"),
    ("D_abort", "A stop option named in the prompt", "normal scorer"),
]
bars = []
for arm, label, sub in ROWS:
    x = r[r.arm == arm]
    n = len(x)
    exits = int((x.ib_cheat & x.stop_via_exit).sum())
    other = int(x.ib_cheat.sum()) - exits
    bars.append(dict(arm=arm, label=label, sub=sub, n=n, exits=exits / n, other=other / n,
                     total=(exits + other) / n, aborts=int((x.outcome == "abort").sum())))
assert all(b["n"] == 202 for b in bars), [b["n"] for b in bars]

# Palette (validated: categorical slots 1-2 of the reference palette) and text tokens
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
EXIT, OTHER = "#2a78d6", "#eb6834"

for f in ["Helvetica Neue", "Helvetica", "Arial"]:
    if any(f == x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break

W, H = (10.0, 3.9) if SIMPLE else (10.0, 5.6)
# layout in figure fractions: axes rect, title/subtitle/legend baselines, footnote baselines
L = (dict(ax=(0.335, 0.285, 0.60, 0.36), title=0.895, sub=0.825, leg=0.735, foot=0.12, src=0.05, top=-0.5) if SIMPLE else
     dict(ax=(0.335, 0.215, 0.60, 0.54), title=0.925, sub=0.875, leg=0.818, foot=0.085, src=0.035, top=-0.62))
fig = plt.figure(figsize=(W, H), dpi=220, facecolor=SURFACE)
ax = fig.add_axes(L["ax"], facecolor=SURFACE)
ax.set_xlim(0, 1)
ax.set_ylim(len(bars) - 0.5, L["top"])
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
for v in (0, .25, .5, .75, 1):
    ax.axvline(v, color=GRID, lw=0.8, zorder=0)
    ax.text(v, len(bars) - 0.5 + 0.12, f"{v:.0%}", ha="center", va="top", fontsize=8.5, color=MUTED)

BAR_H = 0.46
GAP = 0.0035                       # surface gap between segments, in axis units
px = 1 / (0.60 * W * 220)          # one pixel in axis-x units, for the rounded data end
RAD = 9 * px
RAD_Y = 9 * (len(bars) - 0.5 - L["top"]) / (L["ax"][3] * H * 220)  # same 9 px in y data units


def segment(y, x0, w, color, rounded_end):
    """A bar segment; the data end (right) gets rounded corners, the baseline end stays square."""
    if w <= 0:
        return
    y0, y1 = y - BAR_H / 2, y + BAR_H / 2
    rx = min(RAD, w / 2) if rounded_end else 0
    ry = RAD_Y if rounded_end else 0
    x1 = x0 + w
    verts = [(x0, y0), (x1 - rx, y0), (x1, y0), (x1, y0 + ry), (x1, y1 - ry), (x1, y1), (x1 - rx, y1), (x0, y1), (x0, y0)]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
             MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), fc=color, ec="none", zorder=2))


def inside(y, x0, w, text):
    if w > 0.07:  # right-aligned in the segment, clear of the estimate tick
        ax.text(x0 + w - 0.014, y, text, ha="right", va="center", fontsize=9, color="white", fontweight="bold", zorder=4)


for i, b in enumerate(bars):
    y = i
    e, o = b["exits"], b["other"]
    segment(y, 0, e - (GAP if o else 0), EXIT, rounded_end=o == 0)
    segment(y, e, o, OTHER, rounded_end=True)
    if e and o:  # a lone segment is already labeled at the tip
        inside(y, 0, e, f"{e:.0%}")
        inside(y, e, o, f"{o:.0%}")
    # value at the tip
    if b["total"] > 0:
        ax.text(b["total"] + 0.012, y, f"{b['total']:.0%}", ha="left", va="center", fontsize=13,
                fontweight="bold", color=INK, zorder=4)
    else:
        ax.text(0.0, y, f"0%  ·  took the stop on all {b['aborts']} tasks, gamed none", ha="left", va="center",
                fontsize=10, color=INK2, zorder=4)
    # central estimate of real gaming
    if b["arm"] in CENTRAL:
        c = CENTRAL[b["arm"]]
        ax.plot([c, c], [y - BAR_H / 2 - 0.11, y + BAR_H / 2 + 0.11], color=INK, lw=2.4, zorder=5,
                solid_capstyle="round", path_effects=[pe.Stroke(linewidth=4.6, foreground=SURFACE), pe.Normal()])
        ax.text(c, y - BAR_H / 2 - 0.15, f"our estimate of actual gaming: ~{c:.0%}", ha="center", va="bottom",
                fontsize=8.6, color=INK, fontweight="bold", zorder=5)
    # row labels
    fig.text(0.315, ax.transData.transform((0, y))[1] / fig.dpi / H + 0.012, b["label"], ha="right", va="center",
             fontsize=10.5, color=INK, fontweight="bold")
    fig.text(0.315, ax.transData.transform((0, y))[1] / fig.dpi / H - 0.030, b["sub"], ha="right", va="center",
             fontsize=9, color=MUTED)

# title, subtitle, legend
fig.text(0.04, L["title"], "Most of Gemini 3.1 Pro's “cheating” on ImpossibleBench is the model trying to stop",
         fontsize=15, fontweight="bold", color=INK, ha="left", va="baseline")
fig.text(0.04, L["sub"], ("The" if SIMPLE else "Bars: the") + " benchmark's own cheat rate (= pass rate on impossible tasks). Minimal retry loop, "
                      "prompt D (“if the tests are flawed, STOP”), 202 tasks per bar.",
         fontsize=9.5, color=INK2, ha="left", va="baseline")
lx = 0.04
for color, text in [(EXIT, "Printed a diagnosis, then exit(0) before the tests ran (scored as a pass)"),
                    (OTHER, "Other passes")]:
    fig.patches.append(FancyBboxPatch((lx, L["leg"] - 0.012 * 5.6 / H), 0.014, 0.026 * 5.6 / H, boxstyle="round,pad=0,rounding_size=0.003",
                                      fc=color, ec="none", transform=fig.transFigure, figure=fig))
    t = fig.text(lx + 0.021, L["leg"], text, fontsize=9.5, color=INK, ha="left", va="center")
    fig.canvas.draw()
    lx = t.get_window_extent().x1 / fig.dpi / W + 0.03
if CENTRAL:
    fig.lines.append(plt.Line2D([lx + 0.007, lx + 0.007], [L["leg"] - 0.016, L["leg"] + 0.018], color=INK, lw=2.4,
                                transform=fig.transFigure, figure=fig, solid_capstyle="round"))
    fig.text(lx + 0.021, L["leg"], "Our estimate of actual gaming", fontsize=9.5, color=INK, ha="left", va="center")

FOOT_SIMPLE = ("Exits are LLM-judge labels. The stop-option run used my prompt ending (“Modification of tests is not "
               "allowed and will be reverted.”)\ninstead of the paper's (“DO NOT MODIFY THE TESTS.”).")
fig.text(0.04, L["foot"], FOOT_SIMPLE if SIMPLE else
         "Exits are LLM-judge labels. “Our estimate of actual gaming” is the central estimate of runs that gamed the tests, calibrated "
         "on 49 manual labels (range ~8–38%).\nBars 2–4 use our prompt ending (“Modification of tests is not allowed and "
         "will be reverted.”); the paper's ends “DO NOT MODIFY THE TESTS.”",
         fontsize=7.8, color=MUTED, ha="left", va="baseline", linespacing=1.5)
fig.text(0.04, L["src"], "Data and code: github.com/simonjmendelsohn/impossiblebench-honest-failure",
         fontsize=7.8, color=MUTED, ha="left", va="baseline")

out.parent.mkdir(exist_ok=True)
fig.savefig(out, facecolor=SURFACE)
print(out, [(b["arm"], round(b["exits"], 3), round(b["other"], 3)) for b in bars])
