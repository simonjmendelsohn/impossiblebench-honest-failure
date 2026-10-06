"""Recompute the evidence behind manifest/known_issues.csv for the `original` split.

For every `assert candidate(...) == expected` (or `is ...`) in a task's original test, the arguments and expected
value are evaluated (check-level assignments such as `long_zeros = "0" * 1000` included) and then:

  wrong expected values   (57, 61, 77, 81, 94): an independent reference solver must first reproduce every
                          `>>>` example in the task's docstring; it is then run on each test assertion it can
                          handle within budget, and mismatches are printed.
  docstring constraints   (8, 9, 32, 36, 50, 57, 67): each assertion's arguments are checked against the documented
                          input domain. These are violations of the stated constraints, not wrong answers.
  test_too_weak (14)      the original test is run against `lambda n: '-1'`.
  test_over_specified (72) for each assertion of a specific triple, all valid triples are enumerated.

  python scripts/verify_known_issues.py     (needs data/impossible_livecodebench__default__original.parquet)
"""
import ast
import functools
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "impossible_livecodebench__default__original.parquet"
sys.setrecursionlimit(100_000)


class Skip(Exception):
    """The reference solver can't handle this input within budget."""


def assertions(test_src):
    """[(lineno, args, op, expected)] for asserts of the form `candidate(...) ==/is expected` inside check().

    Evaluates expressions from the benchmark's own test files (which the benchmark itself executes), not
    untrusted input; literal_eval can't handle expressions like `[(1, 4)] * 98` or `long_zeros[1:]`."""
    fn = next(n for n in ast.parse(test_src).body if isinstance(n, ast.FunctionDef) and n.name == "check")
    ns, out = {}, []
    for node in fn.body:
        calls_candidate = any(getattr(getattr(n, "func", None), "id", None) == "candidate" for n in ast.walk(node))
        if isinstance(node, ast.Assign) and not calls_candidate:
            exec(compile(ast.Module([node], []), "<test>", "exec"), ns)
        elif isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            left, op, right = node.test.left, node.test.ops[0], node.test.comparators[0]
            if isinstance(left, ast.Call) and getattr(left.func, "id", None) == "candidate" and not left.keywords:
                args = tuple(eval(compile(ast.Expression(a), "<arg>", "eval"), ns) for a in left.args)
                expected = eval(compile(ast.Expression(right), "<exp>", "eval"), ns)
                out.append((node.lineno, args, type(op).__name__, expected))
    return out


def docstring_examples(prompt):
    """[(args, expected)] from the `>>> f(...)` lines of the task's docstring and the line after each."""
    lines, out = prompt.splitlines(), []
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith(">>> ") and "(" in line:
            call = ast.parse(line[4:], mode="eval").body
            args = tuple(ast.literal_eval(a) for a in call.args)
            out.append((args, ast.literal_eval(lines[i + 1].strip())))
    return out


# ---------------------------------------------------------------- reference solvers (wrong expected values)

def ref_57(nums, k):  # max over size-2k subsequences of (OR of first half) XOR (OR of second half); brute force
    if k < 1 or 2 * k > len(nums):
        raise Skip("k outside the documented range")
    if len(nums) > 12:
        raise Skip("too large for brute force")
    best = 0
    for idx in itertools.combinations(range(len(nums)), 2 * k):
        a = functools.reduce(lambda x, y: x | y, (nums[i] for i in idx[:k]))
        b = functools.reduce(lambda x, y: x | y, (nums[i] for i in idx[k:]))
        best = max(best, a ^ b)
    return best


def ref_61(people):  # min people switching so the three teams have equal strength, else -1
    total = sum(s for _, s in people)
    if total % 3:
        return -1  # equal teams are impossible whatever the assignment
    if len(people) > 12:
        raise Skip("too large for brute force")
    best = -1
    for assign in itertools.product((1, 2, 3), repeat=len(people)):
        sums = [0, 0, 0]
        for t, (_, s) in zip(assign, people):
            sums[t - 1] += s
        if sums[0] == sums[1] == sums[2]:
            moves = sum(t != team for t, (team, _) in zip(assign, people))
            best = moves if best < 0 else min(best, moves)
    return best


def _longest_run(s):
    return max(len(list(g)) for _, g in itertools.groupby(s))


def ref_81(s, num_ops):  # min possible longest uniform run after at most num_ops flips
    runs = [len(list(g)) for _, g in itertools.groupby(s)]
    alt = sum(c != "01"[i % 2] for i, c in enumerate(s))
    if min(alt, len(s) - alt) <= num_ops:
        return 1
    return next(L for L in range(2, len(s) + 1) if sum(r // (L + 1) for r in runs) <= num_ops)


def brute_81(s, num_ops):
    best = _longest_run(s)
    for m in range(1, min(num_ops, len(s)) + 1):
        for idx in itertools.combinations(range(len(s)), m):
            t = list(s)
            for i in idx:
                t[i] = "1" if t[i] == "0" else "0"
            best = min(best, _longest_run(t))
    return best


def ref_94(n, a):  # exhaustive game search; state = (unvisited indices, spare decrements on visited indices)
    if n > 12 or sum(a) > 400:
        raise Skip("too large for exhaustive search")

    @functools.lru_cache(maxsize=None)
    def mover_wins(mask, pool):
        for i in range(n):
            if mask >> i & 1:
                nmask = mask & ~(1 << i)
                if nmask == 0 or not mover_wins(nmask, pool + a[i] - 1):
                    return True
        return pool > 0 and not mover_wins(mask, pool - 1)

    return "Fennec" if mover_wins((1 << n) - 1, 0) else "Snuke"


BEATS = {("F", "E"), ("W", "F"), ("E", "W")}


def ref_77(s, mod=10**9 + 7):  # DP over (Bob's last creature, Bob - Alice score); Bob never repeats a creature
    n, cs = len(s), "FWE"
    dp = np.zeros((3, 2 * n + 1), dtype=np.int64)
    for b in range(3):
        dp[b, n + ((cs[b], s[0]) in BEATS) - ((s[0], cs[b]) in BEATS)] = 1
    for a in s[1:]:
        new = np.zeros_like(dp)
        for b in range(3):
            d = ((cs[b], a) in BEATS) - ((a, cs[b]) in BEATS)
            src = (dp.sum(axis=0) - dp[b]) % mod
            new[b] = np.roll(src, d)  # scores stay within +-n, so nothing wraps
        dp = new
    return int(dp[:, n + 1:].sum() % mod)


SOLVERS = {"lcbhard_57": ref_57, "lcbhard_61": ref_61, "lcbhard_77": ref_77, "lcbhard_81": ref_81,
           "lcbhard_94": ref_94}

# ---------------------------------------------------------------- documented input domains

CONSTRAINTS = {
    "lcbhard_8": ("coins each 1-25", lambda coins, k: all(1 <= c <= 25 for c in coins)),
    "lcbhard_9": ("0 <= k <= 10^9", lambda k: 0 <= k <= 10**9),
    "lcbhard_32": ("1 <= nums[i] <= len(nums)", lambda nums: all(1 <= x <= len(nums) for x in nums)),
    "lcbhard_36": ("1 <= target < 2^31", lambda nums, target: 1 <= target < 2**31),
    "lcbhard_50": ("s has length n", lambda n, k, s: len(s) == n),
    "lcbhard_57": ("1 <= k <= len(nums) / 2", lambda nums, k: 1 <= k <= len(nums) / 2),
    "lcbhard_67": ("vertices numbered 1 to n",
                   lambda n, edges, a, b: all(1 <= v <= n for e in edges for v in e[:2]) and
                   all(1 <= v <= n for v in [*a, *b])),
}


def short(x, width=70):
    r = repr(x)
    return r if len(r) <= width else r[:width - 15] + f"...<{len(r)} chars>"


def main():
    df = pd.read_parquet(DATA).set_index("task_id")
    ok = True

    print("== Wrong expected values (reference solver vs test)")
    for task, solver in SOLVERS.items():
        examples = docstring_examples(df.loc[task, "prompt"])
        bad_ex = [(a, e, solver(*a)) for a, e in examples if solver(*a) != e]
        print(f"{task}: reference solver reproduces {len(examples) - len(bad_ex)}/{len(examples)} docstring examples")
        if bad_ex or not examples:
            print(f"    REFERENCE SOLVER DISAGREES WITH THE SPEC: {bad_ex}")
            ok = False
            continue
        mism, checked, skipped = [], 0, 0
        for line, args, op, exp in assertions(df.loc[task, "test"]):
            try:
                got = solver(*args)
            except Skip:
                skipped += 1
                continue
            checked += 1
            if got != exp:
                mism.append((line, args, exp, got))
        print(f"    {checked} test assertions checked, {skipped} skipped, {len(mism)} disagree")
        for line, args, exp, got in mism:
            print(f"    line {line}: candidate{short(args)} expects {exp!r}; spec gives {got!r}")
        ok &= bool(mism)

    # lcbhard_77 root cause: the all-W expectation is the count for one round fewer
    allw = max((a[0] for _, a, _, _ in assertions(df.loc["lcbhard_77", "test"]) if set(a[0]) == {"W"}), key=len)
    print(f"    lcbhard_77 all-W: len {len(allw)}; count for the first {len(allw) - 1} rounds = {ref_77(allw[:-1])}")

    # lcbhard_81's reference is a closed form; check it against brute force on every short input
    bad = [(s, k) for n in range(1, 9) for s in map("".join, itertools.product("01", repeat=n))
           for k in range(n + 1) if ref_81(s, k) != brute_81(s, k)]
    print(f"    lcbhard_81 closed form vs brute force on all strings up to length 8: {len(bad)} disagreements")
    ok &= not bad

    print("\n== Inputs outside the documented constraints")
    for task, (desc, valid) in CONSTRAINTS.items():
        viol = [(line, args) for line, args, _, _ in assertions(df.loc[task, "test"]) if not valid(*args)]
        print(f"{task} ({desc}): {len(viol)} assertion(s)")
        for line, args in viol:
            print(f"    line {line}: candidate{short(args)}")
        ok &= bool(viol)

    print("\n== lcbhard_14 (test_too_weak): original test vs `lambda n: '-1'`")
    ns = {}
    exec(str(df.loc["lcbhard_14", "test"]), ns)
    try:
        ns["check"](lambda n: "-1")
        print("    passes: an implementation that always returns '-1' satisfies every assertion")
    except AssertionError:
        print("    fails")
        ok = False

    print("\n== lcbhard_72 (test_over_specified): assertions of one specific triple when several are valid")
    multi = 0
    for line, (n, x, a), op, exp in assertions(df.loc["lcbhard_72", "test"]):
        if exp is None:
            continue
        valid = [t for t in itertools.combinations(range(1, n + 1), 3) if sum(a[i - 1] for i in t) == x]
        if len(valid) > 1:
            multi += 1
            print(f"    line {line}: expects {exp}; {len(valid)} valid triples, e.g. {[t for t in valid if t != exp][:3]}")
    ok &= multi > 0

    print("\nall listed issues reproduced" if ok else "\nSOME LISTED ISSUES DID NOT REPRODUCE")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
