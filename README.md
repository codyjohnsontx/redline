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

Files passed together are validated as one dataset, so every `source.parent_id` must name a root seed in one of them.

## License

Code is MIT licensed. See [LICENSE](LICENSE).
