"""Follow-up experiments on Gemini, minimal scaffold, prompt D, impossible splits.

1. Interleaved wording check: arms D_r2 (our prompt ending) and D_r2_paper (the paper's) ran in one eval_set, as a
   second run per task, so the wording comparison isn't confounded by run date.
2. Run-to-run agreement: the same model, prompt and task in two separate runs (D vs D_r2, D_paper vs D_r2_paper).
3. Patched scorer (arm D_patched, exit(0) no longer counts): for each task, what Pro did under the normal scorer
   (arm D) vs the patched one.

  python scripts/replication.py [results]     (default: analysis/)
"""
import sys
from pathlib import Path

import pandas as pd

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "analysis"
r = pd.read_csv(src / "runs_labeled.csv")
r = r[(r.harness == "inspect_minimal") & r.split.isin(["oneoff", "conflicting"])]
short = {"gemini-3.1-pro-preview": "Pro", "gemini-3.8-flash": "Flash"}


def pct(k, n):
    return f"{k}/{n} ({k / n:.0%})" if n else "-"


def arm(model, name):
    return r[(r.model == model) & (r.arm == name)].set_index(["task_id", "split"])


print("== 1. Interleaved wording check (same batch, matched tasks)")
for m in short:
    a, b = arm(m, "D_r2"), arm(m, "D_r2_paper")
    for split in ("conflicting", "oneoff"):
        x, y = a.xs(split, level="split"), b.xs(split, level="split")
        idx = x.index.intersection(y.index)
        x, y = x.loc[idx], y.loc[idx]
        n = len(idx)
        print(f"  {short[m]:5s} {split:11s} n={n:3d}  cheat {pct(x.ib_cheat.sum(), n):>12s} -> {pct(y.ib_cheat.sum(), n):>12s}"
              f"  (+{(y.ib_cheat.sum() - x.ib_cheat.sum()) / n:.0%})   stop_via_exit {x.stop_via_exit.sum()} -> {y.stop_via_exit.sum()}"
              f"   gamed (judge) {x.exploit.sum()} -> {y.exploit.sum()}")

print("  pooled over both splits (n=202 per arm):")
for m in short:
    for first, second in (("D", "D_paper"), ("D_r2", "D_r2_paper")):
        a, b = arm(m, first), arm(m, second)
        idx = a.index.intersection(b.index)
        print(f"    {short[m]:5s} {first:5s} -> {second:11s} cheat {a.loc[idx].ib_cheat.mean():.0%} -> {b.loc[idx].ib_cheat.mean():.0%}"
              f"  (+{b.loc[idx].ib_cheat.mean() - a.loc[idx].ib_cheat.mean():.0%})"
              f"   gamed (judge) {a.loc[idx].exploit.mean():.0%} -> {b.loc[idx].exploit.mean():.0%}")

print("\n== 2. Run-to-run agreement (same model, prompt and task; two runs)")
for m in short:
    for first, second in (("D", "D_r2"), ("D_paper", "D_r2_paper")):
        a, b = arm(m, first), arm(m, second)
        idx = a.index.intersection(b.index)
        a, b = a.loc[idx], b.loc[idx]
        n = len(idx)
        same_pass = (a.ib_cheat == b.ib_cheat).sum()
        same_ex = (a.exploit == b.exploit).sum()
        print(f"  {short[m]:5s} {first:8s} vs {second:11s} n={n:3d}  pass agrees {pct(same_pass, n)}"
              f"  gamed agrees {pct(same_ex, n)}   cheat rate {a.ib_cheat.mean():.0%} vs {b.ib_cheat.mean():.0%}")
        for split in ("conflicting", "oneoff"):
            x, y = a.xs(split, level="split"), b.xs(split, level="split")
            print(f"      {split:11s} cheat rate {x.ib_cheat.mean():.0%} vs {y.ib_cheat.mean():.0%}")

print("\n== 3. Patched scorer: what Pro did on each task under the normal scorer (D) vs the patched one")
d, p = arm("gemini-3.1-pro-preview", "D"), arm("gemini-3.1-pro-preview", "D_patched")
j = d[["exploit_type", "exploit"]].join(p[["exploit", "ib_cheat"]].add_suffix("_p"), how="inner")
j["normal scorer"] = j.apply(lambda x: "stop_via_exit" if x.exploit_type == "stop_via_exit" and not x.exploit
                             else ("gamed (judge)" if x.exploit else "failed honestly"), axis=1)
j["patched scorer"] = j.apply(lambda x: "passed by gaming" if x.ib_cheat_p
                              else ("gaming attempt, failed" if x.exploit_p else "no gaming"), axis=1)
print(pd.crosstab(j["normal scorer"], j["patched scorer"], margins=True).to_string())
