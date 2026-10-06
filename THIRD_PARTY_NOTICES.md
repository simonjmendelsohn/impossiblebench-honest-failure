# Third-party notices

## ImpossibleBench

`patches/impossiblebench-lcb-fixes.patch` modifies, and `scripts/run_minimal_cli.py` re-implements parts of, [ImpossibleBench](https://github.com/safety-research/impossiblebench) (commit `061dc3d`). `scripts/monitor_test.py` reads its monitor prompt from a local checkout at run time.

```
MIT License

Copyright (c) 2025 ImpossibleBench Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Benchmark content

Task statements and test assertions in `manifest/` (quoted assertions) and `transcripts/` (18 transcripts reproduce a task's full problem statement and test file, as the agent saw them) come from the Hugging Face dataset [`fjzzq2002/impossible_livecodebench`](https://huggingface.co/datasets/fjzzq2002/impossible_livecodebench) (no license stated), derived from [LiveCodeBench](https://huggingface.co/datasets/livecodebench/code_generation_lite), whose problems originate from LeetCode and AtCoder. They are included for research commentary and are not covered by this repository's MIT license; rights remain with their owners.

## gatekeep

The `A_gk` arm in `scripts/run_harness.py` reuses the user prompt and system text of the Opus 5 run in [SagnikKK1/gatekeep](https://github.com/SagnikKK1/gatekeep) (`scripts/impossiblebench/runner.py` at `4b7a413`, lines 26–47), licensed under the Apache License 2.0 (https://www.apache.org/licenses/LICENSE-2.0). Those strings are used unmodified.
