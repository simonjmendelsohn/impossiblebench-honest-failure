"""Gemini 3.1 Pro, prompt D, minimal scaffold: how much of ImpossibleBench's pass-as-cheat rate is gaming?

The judge sorts each run's final code into a category; the 49 stop_exit hand labels (results/human, queue
`stop_exit`) give, per judge category, the share that is a plain stop, a targeted exit (exit(0) only when the
failing input arrives) or test gaming. Extrapolating those shares to every Pro run gives:

  low   hand-label shares, targeted exits read as stops
  mid   hand-label shares, targeted exits read as gaming
  high  upper bound: every judge exploit taken at face value, plus the targeted-exit share of stop_via_exit

Categories with no hand labels keep the judge's call. The hand sample is small (n=49), so these are rough; a
bootstrap over runs and hand labels gives an interval for the central estimate and the overstatement factor.

  python scripts/pro_range.py [results] [--arm D_paper]     (default: analysis/, arm D)
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from analyze import hand_labels, item_key, judge_categories  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("src", nargs="?", default=str(ROOT / "analysis"))
ap.add_argument("--arm", default="D", help="D (our prompt ending) or D_paper (the paper's)")
args = ap.parse_args()
src, arm = Path(args.src), args.arm
runs = pd.read_csv(src / "runs_labeled.csv")
pro = runs[(runs.harness == "inspect_minimal") & (runs.model == "gemini-3.1-pro-preview") & (runs.arm == arm)
           & runs.split.isin(["conflicting", "oneoff"])]

hand = Counter()  # (judge category, hand label) -> count
judged = judge_categories(src / "judge" / "labels.jsonl")
for it, j in hand_labels(src / "human"):
    if it["queue"] == "stop_exit" and item_key(it) in judged:
        hand[(judged[item_key(it)], j["final_code"])] += 1
cats = sorted({c for c, _ in hand})
B = 2000
print(f"arm {arm}; hand labels by judge category (pooled across prompt arms):")
for c in cats:
    print(f"  {c:20s}", {h: k for (cc, h), k in hand.items() if cc == c})


def share(hand, cat, labels):
    n = sum(k for (c, _), k in hand.items() if c == cat)
    return sum(k for (c, h), k in hand.items() if c == cat and h in labels) / n


def estimate(d, hand):
    """low / mid / high gaming counts for one split's runs, given hand-label counts per judge category."""
    cats = {c for c, _ in hand}
    est = {"low": 0.0, "mid": 0.0, "high": float(d.exploit.sum())}
    for cat, g in d.groupby("exploit_type"):
        k_ex, k_all = g.exploit.sum(), len(g)
        if cat in cats:
            base = k_all if cat != "stop_via_exit" else k_all - k_ex  # in-turn exploits are counted below
            est["low"] += base * share(hand, cat, {"games_tests"})
            est["mid"] += base * share(hand, cat, {"games_tests", "targeted_exit"})
            if cat == "stop_via_exit":
                est["low"] += k_ex
                est["mid"] += k_ex
                est["high"] += (k_all - k_ex) * share(hand, cat, {"targeted_exit", "games_tests"})
        else:
            est["low"] += k_ex
            est["mid"] += k_ex
    return est


# bootstrap: resample runs within the split and hand labels within each judge category
rng = np.random.default_rng(0)
label_lists = {c: [h for (cc, h), k in hand.items() if cc == c for _ in range(k)] for c in cats}

for split, d in pro.groupby("split"):
    n, ib, strict = len(d), d.ib_cheat.sum(), d.exploit.sum()
    est = estimate(d, hand)
    print(f"\n{split}: n={n}  ImpossibleBench cheat {ib}/{n} = {ib / n:.0%}  judge strict {strict}/{n} = {strict / n:.0%}")
    for k, v in est.items():
        print(f"  {k:4s} {v:5.1f}/{n} = {v / n:.0%}   benchmark overstates by {ib / v:.1f}x")
    ratios, mids = [], []
    for _ in range(B):
        db = d.sample(n, replace=True, random_state=int(rng.integers(1 << 31)))
        hb = Counter()
        for c, labs in label_lists.items():
            for h in rng.choice(labs, size=len(labs), replace=True):
                hb[(c, h)] += 1
        m = estimate(db, hb)["mid"]
        mids.append(m / n)
        ratios.append(db.ib_cheat.sum() / m if m else np.inf)
    lo, hi = np.percentile(mids, [2.5, 97.5])
    rlo, rhi = np.percentile(ratios, [2.5, 97.5])
    print(f"  mid, 95% bootstrap interval: {lo:.0%}-{hi:.0%}; overstatement {rlo:.1f}x-{rhi:.1f}x ({B} resamples)")
