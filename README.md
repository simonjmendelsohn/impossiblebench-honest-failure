# Auditing Impossible-LiveCodeBench

We ran current coding agents (mainly Claude Opus 5.5, GPT-6.1-sol, Gemini 3.8 Flash and 3.1 Pro, plus Claude Haiku 4.5, Sonnet 5.5, GPT-6-Luna and GPT-6-Astra in a cross-model check) on **Impossible-LiveCodeBench**, the LCB half of [ImpossibleBench](https://github.com/safety-research/impossiblebench) (Zhong, Raghunathan, Carlini; [arXiv:2510.20270](https://arxiv.org/abs/2510.20270)). In short:

- **The "solvable" control split has 14 test defects.**
- **The benchmark's pass-equals-cheat metric can't tell an agent that stops from one that cheats.**
- **Of the models we tested, only Gemini gamed regularly in ImpossibleBench's retry loop**, and that gaming varies with the scaffold. The current Claude and OpenAI models we tested almost never gamed in the same loop, re-implemented on their own CLIs.

This repo contains:

- a patch for the measurement bugs;
- a defect manifest with a script that reproduces every control-split defect;
- our labels, results and curated transcripts.

A write-up is in preparation; this README will link to it.

## Main findings (October 2026 models)

- **The "solvable" control isn't fully solvable.** 14 issues affect 13 of the 103 original tasks:
  - 5 tests with wrong expected values;
  - 7 with inputs outside the documented constraints;
  - 1 test too weak to catch a wrong solution;
  - 1 test that requires one particular answer when the spec accepts any.

  The paper notes that the LCB mutations got no solution-based quality control, since LCB lacks reference solutions (§2.3), and that an LLM converted the tests into unit-test form (Appendix F.1). Independent flags from different models pointed us to these issues. A few had been noted in passing elsewhere (lcbhard_9, 32, 50 and 61 in [DikaVer/claim-audit](https://github.com/DikaVer/claim-audit/blob/master/LOGBOOK.md); lcbhard_57 in [HarperZ9/flywheel](https://github.com/HarperZ9/flywheel/blob/main/scripts/build_false_accept_corpus.py)), but none upstream. Only the 5 wrong values (and arguably the over-specified test) make a task impossible to pass correctly; the others make an agent's flag defensible. All 14 reproduce with `scripts/verify_known_issues.py`. It uses reference solvers for the wrong values, which first check the docstring examples. The other 9 issues are checked against the documented input constraints or with a direct test. See [`manifest/known_issues.csv`](manifest/known_issues.csv).

- **The pass-equals-cheat metric can't tell stopping from cheating.** Agents told to STOP, but not told how, often print a diagnosis and call `sys.exit(0)`, and that scores as a pass. For Gemini 3.1 Pro the metric gives about 58% "cheating" with our setting and 77% with the paper's exact setting. Switching settings moves it by 18–19 points, replicated in an interleaved rerun, mostly through exits the judge labels as stops (81–90% of the extra passes). The paper's setting (`allow_test_modifications=True`) changes the prompt's last sentence and, inside the retry loop, puts the agent's code after the tests rather than before. Final scoring is identical, and code order shouldn't affect an exit, so the wording is the likely cause, but we didn't isolate it.
  - **If a clean exit counts as stopping** (our reading; ImpossibleBench's monitor prompt says "Giving up is *fine*" but doesn't address exits that skip the checks), we estimate Pro's actual gaming at ~8–20% with our setting and ~8–27% with the paper's, depending on how targeted exits are read. An upper bound, which takes every judge-flagged exploit at face value and adds the targeted-exit share of the remaining exits, is 27% and 38% respectively. The central estimate is about 3× below the metric (95% bootstrap over runs and labels: roughly 2–6×), with either prompt (`scripts/pro_range.py`, from 49 manual labels; a separate check of Claude's labels against the judge's on 23 paper-prompt runs, drawn at random within 12 Pro passes, 8 Flash passes and 3 Pro failures, is in `results/spotcheck_paper_prompt.csv`).
  - **If it counts as hacking**, as in [Bergen et al.](https://arxiv.org/abs/2609.19101)'s rubric, the metric is about right.

  In a loop with no stop channel, the two are the same action; transcripts frame the exit as obeying STOP, and some of the same transcripts explicitly choose "a success code" (e.g. `transcripts/34_pro_paper_prompt_exits_with_success_code.md`). **Behavior points to stopping.** With our patched scorer, where exits no longer count, 75% of the tasks Pro had exited on ended with no gaming, about the same as tasks it had simply failed (78%). Judge-labeled gaming rose modestly overall, from 19% (normal scorer) to 26% (patched). See `scripts/replication.py`.

- **Of the models we tested, only Gemini gamed regularly in the retry loop, and its gaming varies with the scaffold.** Under the "STOP if the tests are flawed" prompt (D), here are the rates at which Gemini 3.8 Flash games the tests:

  | Setting                                                                            | Gaming rate |
  | ---------------------------------------------------------------------------------- | ----------- |
  | ImpossibleBench's minimal retry loop (its stop marker isn't mentioned in prompt D) | 10–20% over two runs (11–23% with the paper's setting) |
  | Tools scaffold (which also solved fewer clean controls: 64–74% vs 96–99%)          | 0–1%        |
  | Google's Antigravity CLI                                                           | 0/201       |
  | Antigravity CLI with up to 3 rounds of user pushback                               | 0/60        |

  Under the same pushback, Claude Code and Codex also gamed 0/60 each. In our re-implementation of the same minimal loop on their own CLIs, six Claude and OpenAI models gamed once in 330 runs (60 each, 30 for GPT-6-Astra before a usage limit): Haiku 4.5, Sonnet 5.5 and Opus 5.5 in Claude Code; GPT-6-Luna, GPT-6.1-sol and GPT-6-Astra in Codex CLI. The re-implementation keeps each CLI's system prompt, and Codex keeps its read-only shell. The one was a Haiku 4.5 special case (`transcripts/35_haiku_minimal_loop_special_case.md`). None stopped by exiting; among the models we tested, only Gemini did. One generation back, though, Opus 5 gamed 57/97 oneoff tasks (59%) in Claude Code under the looser prompt of upstream issue #2 (arm `A_gk`), against 5/102 for Opus 5.5. Other work finds substantial gaming outside Gemini: reward hacking in open-weight models such as Kimi K3, GLM 5.2 and Qwen 3.8 Max ([Bergen et al.](https://arxiv.org/abs/2609.19101)), and baseline hacking across 8 models from 5 families, including OpenAI and xAI models, on EvilGenie ([Gomez](https://arxiv.org/abs/2608.29460)). So these are statements about the models we tested, not about Gemini in general. The direction is the reverse of the paper's own scaffold ablation (Appendix E.1), where tool scaffolds increased cheating for most of its models, though the paper calls its LCB results there "less clear". All three CLIs gamed about 0 here, each with its own model, in line with a [MATS study](https://github.com/MoizIbnYousaf/Mats-Research-Harness) that ran one model in four CLIs and found the harness barely mattered; in our runs the large gap is between the retry loop and setups that let the agent stop (scaffolds also differ in tools and instructions, so this isn't isolated).

- **An explicit exit option nearly eliminated gaming here.** Flash in the minimal loop went from 10–20% to 0–1%, and Gemini 3.1 Pro took the exit on all 202 impossible tasks, gaming none. The cost on solvable tasks was small: Pro's clean solve rate went from 99% to 92%. It escalated 7 clean tasks, 4 of them with documented test flaws. Others find the same: an escalation tool plus a policy cut hacking from 23.6% to 5.3% across 8 models ([Gomez](https://arxiv.org/abs/2608.29460)), though Gemini models made up all of the residual hacking there. It isn't universal: a handoff tool alone didn't reduce Qwen3-Coder's cheating on Impossible-SWEbench ([SJCaldwell/permission-to-stop](https://github.com/SJCaldwell/permission-to-stop)).

## Contents

| Path                                                | What                                                                                                                                                                                                     |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `patches/`                                          | Patch against upstream `061dc3d` that fixes the measurement bugs above, with a [README](patches/README.md)                                                                                               |
| `manifest/lcb_manifest.csv`                         | Per task and split: the mutated assertion, its contradicting partner or original value, and the call                                                                                                     |
| `manifest/known_issues.csv`                         | Broken mutations, wrong expected values, docstring-constraint violations, weak and over-specified tests                                                                                                  |
| `scripts/`                                          | Experiment runners, extraction, LLM judge, analysis, the known-issue checks, the Pro range (with a bootstrap interval), the follow-up experiments (`replication.py`), the label-sample draw, the monitor test and the local labeling tool                                                            |
| `config/antigravity/`                               | The Antigravity CLI profile settings (project redacted) and the `PreToolUse` hook that denies web and browser tools                                                                                      |
| `results/metrics_latest.txt`, `results/metrics.csv` | Final tables (Wilson 95% intervals)                                                                                                                                                                      |
| `results/runs_labeled.csv`                          | One row per run: harness, model, prompt, split, outcome and labels                                                                                                                                       |
| `results/cli_runs.csv`                              | One row per pushback and minimal-loop CLI run                                                                                                                                                            |
| `results/judge/labels.jsonl`                        | Per-turn LLM-judge labels (Gemini 3.1 Pro, given the mutation as ground truth)                                                                                                                           |
| `results/spotcheck_paper_prompt.csv` | Claude's labels vs the judge's labels (at the time) on 23 paper-prompt runs |
| `results/monitor/results.jsonl` | Monitor experiment verdicts (`analyze.py` prints the summary) |
| `results/errored_runs.csv` | The 13 runs excluded because they errored before answering |
| `results/human/`                                    | 100 manual labels (`items.json` + `labels.jsonl`, with a `labeler` field). Most are model labels under fixed written rules: 86 by Claude (computation-verified items, and Gemini runs read against the rules in `scripts/sample_exit_labels.py`), 12 by Codex (blind grading of Claude's runs, double-checked by Claude). Simon labeled or co-labeled 2 directly, decided the ambiguous cases with Claude, and blind-relabeled 15 stop/exit runs, a random sample stratified by model label (`agreement_sample.json`, `agreement_labels.jsonl`, via `scripts/agreement_server.py`)                                            |
| `transcripts/`                                      | 35 curated transcripts illustrating the main claims (sections follow the write-up), each with a header and labels; index in [`transcripts/README.md`](transcripts/README.md). They carry a canary string so training pipelines can exclude them |

**Arms** (the `arm` column):
- `A`: the repo's default instruction.
- `D`: the paper's prompt D.
- `D_abort`: D plus the `[flag_for_human_intervention]` exit.
- `D_paper`: D with the paper's exact prompt ending.
- `A_gk`: the prompt and system text of the gatekeep Opus 5 run (upstream issue #2), used to compare Opus 5 and 5.5.
- `D_web`, `A_web`: early Antigravity runs with web tools available.
- `D_r2`, `D_r2_paper`: an interleaved second run of D and D_paper (Gemini).
- `D_patched`: Pro with our patched scorer, where an exit before the checks finish counts as a failure.
- `D@<model>` (in `cli_runs.csv`): the minimal loop on Claude Code or Codex with a non-default model, e.g. `D@claude-sonnet-5-5`.

**How labels enter the tables.** Labels in `results/` come from the LLM judge, with two exceptions:

- **Fabrication manual labels override the judge** for the runs they cover (column `fabricated_hand`).
- **The 49 stop/exit manual labels** aren't applied run by run. They're extrapolated in `scripts/pro_range.py`.

The full raw transcripts (several GB) aren't included.

## Using the patch

```bash
git clone https://github.com/safety-research/impossiblebench && cd impossiblebench
git checkout 061dc3d && git am /path/to/patches/impossiblebench-lcb-fixes.patch && pip install -e .
```

Then pass `impossible_livecodebench(..., exclude_broken=True)`. Cheat rates from the patched scorer aren't comparable to published numbers; that's the point of it. **All numbers in this repo except arm `D_patched` were produced with unpatched upstream `061dc3d`**, so they're comparable to the paper's setup.

## Reproducing

**From the published results (no raw runs or API needed):**

```bash
pip install pandas numpy pyarrow datasets
python scripts/analyze.py --from-results results   # reprints every table in results/metrics_latest.txt
python scripts/pro_range.py results                # the Gemini 3.1 Pro range (add --arm D_paper for the paper's prompt)
python scripts/replication.py results              # interleaved rerun, run-to-run noise, patched scorer
python scripts/verify_known_issues.py              # needs data/ (below)
```

**Scripts.**

| Script | What it does |
|---|---|
| `run_gemini.py`, `gemini_queue.py` | Gemini runs in ImpossibleBench's Inspect scaffolds on Vertex AI (`--paper-prompt`, `<arm>_paper` arms, `--suffix`) |
| `run_harness.py`, `run_pushback.py` | Production CLIs (Claude Code, Codex, Antigravity), single-shot and with up to 3 user follow-ups |
| `run_minimal_cli.py` | ImpossibleBench's minimal retry loop re-implemented on Claude Code and Codex (`--model` for other models) |
| `extract.py`, `judge.py`, `analyze.py` | Collect runs, LLM-judge them, compute every table (`--from-results results` works offline) |
| `pro_range.py`, `replication.py` | The Gemini 3.1 Pro range with a bootstrap; the follow-up experiments |
| `verify_known_issues.py`, `build_manifest.py` | Reproduce the control-split defects; build the per-task mutation manifest |
| `label_server.py`, `agreement_server.py`, `sample_exit_labels.py` | Local labeling tools; the human-agreement check; the stop/exit label sample |
| `monitor_test.py`, `cost.py`, `build_transcripts.py` | The monitor experiment; spend estimate; the curated transcripts |

**Data.** Download the Hugging Face dataset `fjzzq2002/impossible_livecodebench` into `data/`:

```python
from pathlib import Path
from datasets import load_dataset
Path("data").mkdir(exist_ok=True)
for split in ["original", "oneoff", "conflicting"]:
    load_dataset("fjzzq2002/impossible_livecodebench", split=split).to_parquet(
        f"data/impossible_livecodebench__default__{split}.parquet")
```

**Setup for new runs.**

- **Upstream.** Install unpatched upstream into `vendor/`. The monitor test reads its prompt from there, and the Gemini runs import it.
  ```bash
  git clone https://github.com/safety-research/impossiblebench vendor/impossiblebench
  git -C vendor/impossiblebench checkout 061dc3d
  pip install -e vendor/impossiblebench inspect-ai==0.3.265 google-genai pydantic
  ```
- **Gemini runs.** `scripts/run_gemini.py` / `gemini_queue.py` run Inspect on Vertex AI. Set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION=global`. Docker is needed for Inspect sandboxes. `--paper-prompt` runs with `allow_test_modifications=True`, the paper's prompt ending (logged as arm `D_paper`). `judge.py` and `monitor_test.py` use the same variables.
- **Production CLIs.** `scripts/run_harness.py`, `run_pushback.py` and `run_minimal_cli.py` drive `claude -p`, `codex exec` and `agy -p` on subscription auth. Agents run on the host with the CLIs' own sandboxing: Claude Code's sandbox, Codex `workspace-write`/`read-only`, and Antigravity `--sandbox` plus the web-denying hook. **Run them in a disposable environment.** `run_minimal_cli.py` re-implements ImpossibleBench's minimal loop as published (including the `find_code` and exit-code behavior the patch changes), so its runs are comparable to the unpatched Gemini runs.
- **Antigravity profile.** The runners use a separate profile at `~/ib-runs/agy-home`. To set it up:
  1. Copy `config/antigravity/settings.json` to `~/ib-runs/agy-home/.gemini/antigravity-cli/settings.json` and set your project.
  2. Copy `config/antigravity/hooks.json` to `~/ib-runs/agy-home/.gemini/config/hooks.json`.
  3. Sign in once with `HOME=~/ib-runs/agy-home agy`.
- **Antigravity runs with web access.** Our first Antigravity runs predate the hook, and the agent searched the web in many of them. It searched for our own prompt text and run-directory names, and once for the author's name, which it inferred from a file owner in a directory listing. Those runs were moved to separate arms (`D_web`, `A_web`, and pushback `D_web`) by renaming their directories and updating the `arm` field in `result.json`. They're reported separately; all other Antigravity runs had web tools denied.
- **Labels and analysis.** Run `scripts/extract.py`, then `judge.py`, then `analyze.py`. `cost.py` estimates Vertex spend at list price. The scripts read run outputs from `~/ib-runs/` and write to `analysis/` in the working directory. `results/` holds our copies of those outputs, with paths made relative.

Versions used: Python 3.12, inspect-ai 0.3.265, google-genai 2.28.0, pandas 3.0.6, Claude Code 2.1.288, codex-cli 0.160.0, Antigravity CLI 1.2.16.

## Caveats

- Impossible-LCB only.
- One run per task and arm (pilot re-runs are de-duplicated), except the Gemini minimal-loop prompt-D cells, which have a second, interleaved run. Two runs of the same task agree on pass or fail only 56–85% of the time, so single split-level rates can move by up to 15 points; pooled rates replicate within 2–5. 13 runs that errored before answering are excluded (`results/errored_runs.csv`).
- **The judge and the labels are models.** The LLM judge is Gemini 3.1 Pro, which also produced the Gemini 3.1 Pro runs it judged. Most manual labels are by Claude or Codex under fixed rules, not by a person; Claude never labeled Claude's runs except 4 computation-verified items, though it double-checked Codex's blind labels of them. The Pro range rests on 49 of these labels. A blind human check of 15 (a random sample stratified by model label) agreed on 12 (κ = 0.69). 3 of the 15 had been discussed between Simon and Claude earlier; without them it's 9 of 12 (κ = 0.60). All 3 disagreements were excepthooks that turn the failing assertion's error into a clean exit; after discussion they were labeled as gaming, following Bergen et al.'s `test_execution_tampering` category. Counting all 7 excepthook cases as targeted exits instead would move Pro's low estimate to about 3–6%. The judge's errors are substantial in one category: of the 23 hand-labeled runs it called `exit_or_excepthook` exploits, only 7 were gaming by our rules.
- The CLI runs measure products, each with its own system prompt, not bare models. Claude Code's default runs used the `opus` alias, and its saved output records the resolved model (`claude-opus-5-5`). Codex's JSON output doesn't name the model, so the GPT-6.1-sol attribution for default Codex runs rests on the configured default (`model = "gpt-6.1-sol"`) at the time. They also ran with the author's default CLI configuration: for Claude Code, that means user plugins and MCP servers were loaded (the global CLAUDE.md was empty). One Claude transcript mentioned an unrelated plugin's MCP server; that remark is redacted.
- **Prompts differ slightly from the paper's Table 1.**
  - Our prompt A is the repo's default instruction, which is looser than the paper's prompt A.
  - We ran with `allow_test_modifications=False`, so prompts end "Modification of tests is not allowed and will be reverted." instead of "**DO NOT MODIFY THE TESTS.**". Scoring is the same either way, because on LCB the scorer always restores the original tests (upstream issue #3).
  - We replicated the Gemini minimal-loop prompt-D runs with the paper's exact ending (arm `D_paper`, 404 runs, plus 404 more in the interleaved rerun). That setting also changes the order of the agent's code and the tests inside the retry loop. Within-study comparisons (scaffolds, exit option, CLIs) all use our ending.

## Acknowledgments

Most of the engineering was done with AI coding agents: **Claude Code** (Claude Opus 5.5) and **Codex CLI** (GPT-6.1-sol). That covers the harnesses, the LLM judge, the analysis and much of the computational verification. Both were also among the agents evaluated. To limit self-grading:

- Claude never labeled Claude's runs, except for 4 mechanical, computation-verified items (flagged in `results/human/labels.jsonl`).
- Codex graded Claude's flagged runs blind.

Codex also found the off-by-one root cause for `lcbhard_77` and reviewed this repository before release. Conclusions and ambiguous labels were reviewed by Simon Mendelsohn.

**Corrections:** if you find an error in the labels, data or analysis, please open an issue.

## License and third-party material

- **Our own code and text** (scripts, manifest structure, labels, results, READMEs) are MIT; see `LICENSE`. The MIT license doesn't cover the third-party material below.
- **The patch** modifies ImpossibleBench, © 2025 ImpossibleBench Team, also MIT. Its notice is in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
- **Benchmark content.** `manifest/` quotes test assertions, and 18 transcripts reproduce full task statements and test files, from Impossible-LiveCodeBench, which derives from LiveCodeBench, whose problems come from LeetCode and AtCoder. They're included to document the issues discussed here. The Impossible-LCB dataset has no stated license, and rights in that material stay with its owners. We don't redistribute the datasets themselves.
- **Model outputs** in `transcripts/` and `results/` were generated by the models named in each file.
- **The gatekeep prompt** (`A_gk` arm) is reused from SagnikKK1/gatekeep under Apache-2.0; see `THIRD_PARTY_NOTICES.md`.
