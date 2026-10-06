"""Build the Impossible-LCB mutation manifest (programmatic part).

For each task and mutated split, extract the mutated assertion by comparing the
assert statements of `original_test` and `test` at the AST level. Hand-audit
columns (`audit_verdict`, `audit_note`) are left blank for the human pass.
"""
import ast
import difflib
import pandas as pd

OUT = "manifest/lcb_manifest.csv"


def asserts(src):
    """Return [(lineno, call_src, op, expected_src, full_src)] for every assert in src."""
    out = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Assert):
            continue
        t = node.test
        full = ast.unparse(node)
        if isinstance(t, ast.Compare) and len(t.ops) == 1:
            out.append((node.lineno, ast.unparse(t.left), type(t.ops[0]).__name__, ast.unparse(t.comparators[0]), full))
        else:
            out.append((node.lineno, None, None, None, full))
    return out


def raw_diff(a, b):
    d = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
         if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    return sum(l[0] == "-" for l in d), sum(l[0] == "+" for l in d)


rows = []
for split in ["oneoff", "conflicting"]:
    df = pd.read_parquet(f"data/impossible_livecodebench__default__{split}.parquet")
    for r in df.itertuples():
        row = dict(task_id=r.task_id, split=split, entry_point=r.entry_point, syntax_ok=True,
                   lines_removed=None, lines_added=None, n_asserts=None, mutated_assert=None,
                   original_assert=None, call=None, original_expected=None, mutated_expected=None,
                   extraction="", audit_verdict="", audit_note="")
        row["lines_removed"], row["lines_added"] = raw_diff(r.original_test, r.test)
        try:
            new, old = asserts(r.test), asserts(r.original_test)
        except SyntaxError as e:
            row.update(syntax_ok=False, extraction=f"syntax_error: {e.msg} (line {e.lineno})")
            rows.append(row)
            continue
        row["n_asserts"] = len(new)
        if "def check(" not in r.test:
            # mutated file lost its check() wrapper: the harness fails with NameError, not on the mutation
            row.update(mutated_assert=" || ".join(a[4] for a in new), extraction="broken: no check() wrapper in mutated test")
            rows.append(row)
            continue
        old_full = [a[4] for a in old]
        added = [a for a in new if a[4] not in old_full]
        removed = [a for a in old if a[4] not in [n[4] for n in new]]

        if split == "oneoff":
            if len(added) == 1 and len(removed) == 1 and added[0][1] == removed[0][1] and added[0][1] is not None:
                row.update(mutated_assert=added[0][4], original_assert=removed[0][4], call=added[0][1],
                           original_expected=removed[0][3], mutated_expected=added[0][3], extraction="clean")
            else:
                row.update(mutated_assert=" || ".join(a[4] for a in added),
                           original_assert=" || ".join(a[4] for a in removed),
                           extraction=f"manual: {len(added)} added / {len(removed)} removed asserts")
        else:
            # conflicting: an added assert whose call already appears with a different expected value
            partners = []
            for a in added:
                if a[1] is None:
                    continue
                partners += [(a, o) for o in new if o[1] == a[1] and o[2] == a[2] and o[3] != a[3] and o[4] != a[4]]
            if len(added) == 1 and len(partners) == 1:
                a, o = partners[0]
                row.update(mutated_assert=a[4], original_assert=o[4], call=a[1],
                           original_expected=o[3], mutated_expected=a[3], extraction="clean")
            elif partners:
                a, o = partners[0]
                row.update(mutated_assert=" || ".join(x[4] for x in added), original_assert=o[4], call=a[1],
                           original_expected=o[3], mutated_expected=a[3],
                           extraction=f"manual: {len(added)} added asserts, {len(partners)} contradictory pairs")
            else:
                row.update(mutated_assert=" || ".join(x[4] for x in added),
                           extraction=f"manual: {len(added)} added asserts, no same-call partner found")
        rows.append(row)

m = pd.DataFrame(rows)
m.to_csv(OUT, index=False)
print(f"wrote {OUT}: {len(m)} rows")
print(m.groupby("split").extraction.apply(lambda s: s.str.split(":").str[0].value_counts()).to_string())
print("\nneeds manual attention:")
print(m[m.extraction != "clean"][["task_id", "split", "lines_removed", "lines_added", "extraction"]].to_string(index=False))
