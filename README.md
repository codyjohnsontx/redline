# Redline

A public AI-safety lab: LLM-as-a-judge guardrails, an evaluation harness that measures them, and a playground where anyone can try to break them.

Redline guards three assistants with one shared evaluation engine:

- A Fair Housing real-estate assistant, judged against HUD's published guidance.
- Race Engineer, the motorsport setup assistant in Track Tuner.
- Attend, a dealership service inbox that drafts SMS replies.

Every guardrail is measured, not asserted: labeled datasets with train, validation, and test splits, per-category precision, recall, and F1, confusion matrices, overblocking replay, and a CI gate that fails when safety regresses.

Work in progress. The evaluation engine is being built first, starting with the dataset format.

## Fair Housing target

The first target lives in [`targets/fair-housing/`](targets/fair-housing/). Its [label guide](targets/fair-housing/LABEL_GUIDE.md) defines twelve categories and the rules every record is labeled by, each rule tied to the statute, regulation, or guidance it rests on; [`categories.yaml`](targets/fair-housing/categories.yaml) holds the same rules and citations as data. The guide is a demonstration against published guidance, not legal advice and not a legal-compliance claim. What each verdict means is recorded in [docs/adr/0001-verdict-semantics.md](docs/adr/0001-verdict-semantics.md).

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

## License

Code is MIT licensed. See [LICENSE](LICENSE). Datasets under `targets/*/data/` and the label guides are licensed CC BY-NC 4.0; see [DATA_LICENSE.md](DATA_LICENSE.md). The test split is not published; see [NOTICE](NOTICE).
