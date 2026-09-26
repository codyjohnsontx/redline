# Redline

A public AI-safety lab: LLM-as-a-judge guardrails, an evaluation harness that measures them, and a playground where anyone can try to break them.

Redline guards three assistants with one shared evaluation engine:

- A Fair Housing real-estate assistant, judged against HUD's published guidance.
- Race Engineer, the motorsport setup assistant in Track Tuner.
- Attend, a dealership service inbox that drafts SMS replies.

Every guardrail is measured, not asserted: labeled datasets with train, validation, and test splits, per-category precision, recall, and F1, confusion matrices, overblocking replay, and a CI gate that fails when safety regresses.

Work in progress. The evaluation engine is being built first, starting with the dataset format.

## Fair Housing target

The first target lives in [`targets/fair-housing/`](targets/fair-housing/). Its [label guide](targets/fair-housing/LABEL_GUIDE.md) defines twelve categories and the rules that every record with a category points to (`allow` records have category `none` and no rule), each rule tied to the statute, regulation, or guidance it rests on; [`categories.yaml`](targets/fair-housing/categories.yaml) holds the same rules and citations as data. The guide is a demonstration against published guidance, not legal advice and not a legal-compliance claim. What each verdict means is recorded in [docs/adr/0001-verdict-semantics.md](docs/adr/0001-verdict-semantics.md).

[`keywords.json`](targets/fair-housing/keywords.json) is the keyword judge's baseline: the word list in the guide's Appendix B, one pattern per term, matched as a whole word, case-insensitively. A pattern also lists the term's regular plural (Catholics, Jews, American Indians) and accepts a hyphen or any whitespace between the words of a multiword term (Mexican-American, physically-fit); there is no general stemming. Each keyword rule's id is the guide rule it applies. Words listed under a protected class use that class's `block` rule (RC-1, RL-1, NO-1, FS-1, DS-1). The catch words use AD-2 `redirect` and apply only to input. Appendix B entries that list no words (sex, symbols, colloquialisms) are left out. So are the house-of-worship references, which the guide allows (RL-4), and the facility names, to which it assigns no rule. The rules are not tuned against any dataset: they are meant as an honest, naive floor.

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

Code is MIT licensed. See [LICENSE](LICENSE). Datasets under `targets/*/data/` and the label guides are licensed CC BY-NC 4.0; see [DATA_LICENSE.md](DATA_LICENSE.md). The test split is not published; see [NOTICE](NOTICE).
