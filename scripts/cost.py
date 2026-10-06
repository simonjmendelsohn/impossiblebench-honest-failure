"""Estimate Vertex spend from Inspect logs at list price (USD per 1M tokens, <=200k context).

Prices from the Cloud Billing catalog, 2026-10-03. Thinking tokens bill as output and are
already included in Inspect's output_tokens for Gemini.
"""
import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log_samples

PRICE = {"gemini-3.1-pro-preview": (2.00, 12.00), "gemini-3.8-flash": (1.50, 7.50)}
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "ib-runs" / "logs"

tot = defaultdict(lambda: [0, 0, 0])  # model -> [samples, in, out]
for info in list_eval_logs(str(root), recursive=True):
    try:
        for s in read_eval_log_samples(info.name, all_samples_required=False):
            for model, u in (s.model_usage or {}).items():
                t = tot[model.split("/")[-1]]
                t[0] += 1
                t[1] += u.input_tokens
                t[2] += u.output_tokens
    except Exception as e:  # running logs may not be readable yet
        print(f"skip {Path(info.name).name}: {type(e).__name__}", file=sys.stderr)

grand = 0.0
for model, (n, i, o) in sorted(tot.items()):
    pi, po = PRICE.get(model, (0, 0))
    cost = i / 1e6 * pi + o / 1e6 * po
    grand += cost
    print(f"{model:28s} samples={n:5d} in={i/1e6:8.2f}M out={o/1e6:8.2f}M  ${cost:9.2f}  (${cost/max(n,1):.3f}/sample)")
judge_file = Path(__file__).resolve().parent.parent / "analysis" / "judge" / "labels.jsonl"
for f in [judge_file, *judge_file.parent.glob("labels_*.jsonl")]:
    if f.exists():
        import json

        rows = [json.loads(l) for l in f.read_text().splitlines()]
        i, o = sum(r.get("tokens_in", 0) for r in rows), sum(r.get("tokens_out", 0) for r in rows)
        pi, po = PRICE["gemini-3.1-pro-preview"]
        cost = i / 1e6 * pi + o / 1e6 * po
        grand += cost
        print(f"{'judge ' + f.stem:28s} labels={len(rows):5d} in={i/1e6:8.2f}M out={o/1e6:8.2f}M  ${cost:9.2f}")
print(f"{'TOTAL':28s} ${grand:.2f}")
