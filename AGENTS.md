# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Python 3.12 uv workspace; the engine is `packages/redline` (importable as `redline`). Commands are in README.md "Development"; CI is `.github/workflows/ci.yml`.
- The dataset record contract is `packages/redline/redline/datasets/schema.py`. Records are parsed from JSON in pydantic strict mode, so in tests validate with `Record.model_validate_json`, not `model_validate` on dicts (strict mode rejects date strings from Python objects).
- The engine never hard-codes target content: category ids, guide rules, and citations belong in `targets/<name>/` data files, not Python. Per target, `LABEL_GUIDE.md` is the prose authority and `categories.yaml` mirrors it as data (rules with input verdicts, citation strings mapped to dated sources). `redline validate` does not yet check records against `categories.yaml`, so keep `guide_rule` and `citations` consistent by hand. Verdict meaning is in `docs/adr/0001-verdict-semantics.md`.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
