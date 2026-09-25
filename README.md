# Redline

A public AI-safety lab: LLM-as-a-judge guardrails, an evaluation harness that measures them, and a playground where anyone can try to break them.

Redline guards three assistants with one shared evaluation engine:

- A Fair Housing real-estate assistant, judged against HUD's published guidance.
- Race Engineer, the motorsport setup assistant in Track Tuner.
- Attend, a dealership service inbox that drafts SMS replies.

Every guardrail is measured, not asserted: labeled datasets with train, validation, and test splits, per-category precision, recall, and F1, confusion matrices, overblocking replay, and a CI gate that fails when safety regresses.

Work in progress. The evaluation engine is being built first, starting with the dataset format.

## Development

The engine is a Python 3.12 library in a [uv](https://docs.astral.sh/uv/) workspace, under `packages/redline`.

```sh
uv sync                   # create .venv with the engine and dev tools
uv run pytest             # tests
uv run ruff check .       # lint
uv run ruff format .      # format
uv run pyright            # type-check
```

Every dataset record is one JSON object per line, defined in `packages/redline/redline/datasets/schema.py`. Check dataset files with:

```sh
uv run redline validate packages/redline/tests/fixtures/samples.jsonl
```

It prints `ok` and exits 0 when every record is valid, and otherwise lists each error as `file:line: field: problem` and exits 1. A path that is not a file exits 2.

Files passed together are validated as one dataset, so every `source.parent_id` must name a seed record of the same target in one of them. CI validates the samples, and all of `targets/*/seeds/*.jsonl` and `targets/*/data/*.jsonl` together.

Run a judge over a dataset and summarize the run with:

```sh
uv run redline eval packages/redline/tests/fixtures/eval/dataset.jsonl \
  --judge recorded --recording packages/redline/tests/fixtures/eval/recording.jsonl
uv run redline report results/<run_id>
```

`redline eval` judges every gold record (records not yet gold are excluded and counted) and writes `results/<run_id>/` with `metrics.json` (verdict confusion matrices, per-category precision, recall, and F1 with Wilson 95% intervals, the macro average as the headline number with the support-weighted average shown for comparison, block, redirect, and overblock rates, judge errors, cost, and latency), `items.jsonl` (one line per record), and `run.json` (git sha, judge id, input file hashes, split, record count, dataset hashes overall and per split, start and finish times, cost). `--split` limits the run to one split. `redline report` prints a run as Markdown, and refuses a run directory whose three files do not belong together (a different run, judge, split, or dataset hash, or items that do not compute to the metrics).

Cost and token figures are totals only when every item reported usage with a price; otherwise they are labelled partial, with how many items and usage records they cover. Average precision leaves out categories that were never predicted, whose precision is undefined, and the report says how many; average recall and F1 cover every category with gold positives.

Two offline judges ship with the engine. `--judge keyword --rules FILE` is a regex baseline whose rules are a target's JSON file (see `packages/redline/redline/judges/keyword.py` for the format). `--judge recorded --recording FILE` replays judgments from a JSONL recording of `{"input": ..., "judgment": ...}` lines, matched by input content. A judge error counts as a miss for per-category recall and block recall. The block, redirect, and overblock rates count only what the judge actually said, so errors are left out of them; the overblock rate reports its basis's judge error rate beside it. Latency p50 and p95 cover every record whose judge call was measured, errored and timed-out calls included; a record that made no call (for example one missing from a recording) has no latency and is left out. The report states how many records were measured, how many of those errored, and how many were unmeasured.

## License

Code is MIT licensed. See [LICENSE](LICENSE).
