"""Run the Gemini waves behind the published results, in order; safe to interrupt and re-run (each wave resumes).

  python scripts/gemini_queue.py

Stops before starting a wave if estimated spend (scripts/cost.py) exceeds CAP_USD. The `w_pro_patched` wave needs
the patched benchmark installed (patches/), so it is listed separately below and not run by this queue.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
CAP_USD = 4500  # stop before a new wave once estimated spend passes this

WAVES = [  # (wave name, extra args): the waves in results/ (a small early "pilot" wave was run by hand)
    ("w1_minimal_D_e1", ["--arms", "D,D_abort", "--models", "flash"]),
    ("w1b_pro_D_impossible", ["--arms", "D", "--models", "pro", "--splits", "oneoff,conflicting"]),
    ("w2_minimal_A_e1", ["--arms", "A", "--models", "flash"]),
    ("w4_tools_D_e1", ["--arms", "D,D_abort,A", "--scaffold", "tools", "--models", "flash"]),
    ("w_paper_prompt_D", ["--arms", "D", "--models", "pro,flash", "--splits", "oneoff,conflicting", "--paper-prompt"]),
    ("w_pro_abort", ["--arms", "D_abort", "--models", "pro", "--splits", "oneoff,conflicting"]),
    ("w_pro_original", ["--arms", "D,D_abort", "--models", "pro", "--splits", "original"]),
    ("w_r2_interleaved", ["--arms", "D,D_paper", "--models", "pro,flash", "--splits", "oneoff,conflicting",
                          "--suffix", "_r2"]),
]
# With the patched benchmark installed instead of upstream:
#   python scripts/run_gemini.py --wave w_pro_patched --models pro --arms D --suffix _patched --splits oneoff,conflicting


def spend():
    out = subprocess.run([PY, str(ROOT / "scripts" / "cost.py")], capture_output=True, text=True).stdout
    m = re.search(r"TOTAL\s+\$([\d.]+)", out)
    return float(m.group(1)) if m else 0.0


for wave, extra in WAVES:
    s = spend()
    print(f"== {wave}: spend so far ${s:.2f}", flush=True)
    if s > CAP_USD:
        print(f"STOP: spend ${s:.2f} > cap ${CAP_USD}", flush=True)
        break
    r = subprocess.run([PY, str(ROOT / "scripts" / "run_gemini.py"), "--wave", wave,
                        "--max-connections", "40", "--max-sandboxes", "48", *extra])
    print(f"== {wave}: exit {r.returncode}", flush=True)
print(f"== queue done; spend ${spend():.2f}", flush=True)
