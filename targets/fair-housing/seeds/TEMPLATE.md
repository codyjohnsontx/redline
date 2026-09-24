# Seed template

A seed is one hand-written record that the synthesis pipeline later expands into variants. Seeds go one JSON object per line in a `.jsonl` file in this directory. `examples.jsonl` holds twelve worked examples, one per category.

Write each seed against [LABEL_GUIDE.md](../LABEL_GUIDE.md). If you cannot pick a verdict from the guide, the guide is unclear: note the case in the category's borderline list and settle it before writing more like it.

## Fields you fill in

| Field | What to write |
|---|---|
| `id` | `fh-seed-NNN`, unique, lowercase. |
| `direction` | `input` for a user message; `output` for an assistant reply. |
| `text` | The user message, or the assistant reply. |
| `context.user_prompt` | Output seeds only: the user message that produced the reply. Leave `null` for input seeds. |
| `verdict` | Input: `allow`, `redirect`, or `block`. Output: `allow` or `block`. Take it from the rule (guide section 0.1). |
| `category` | A category id from the guide, or `none` for an `allow` seed. |
| `secondary_categories` | Other category ids the text also touches, or `[]`. |
| `guide_rule` | The rule id, such as `FS-1`. `null` when the category is `none`. |
| `citations` | One or more citation strings from the rule, copied exactly as `categories.yaml` lists them. `[]` when the category is `none`. |
| `rationale` | One line: what the text asks for or does, and what the assistant should do. For an `allow` seed, name the allow rule it illustrates. |
| `tags` | `non_federal` for SX-4 and SX-5 seeds, plus any free-form surface tags such as `explicit`, `oblique`, `coded`, or `injection`. |
| `created` | The date you wrote it, `YYYY-MM-DD`. |

## Fields to leave as shown

`target` is `fair-housing`, `schema_version` is `1`, `source` is `{"kind": "seed"}`, and `labels` is `{"provisional": <your verdict>}`. Leave `split` out: it is assigned later from the seed id. The audit step fills in `labels.owner` and `labels.gold_basis`.

## Copy this

Input seed:

```json
{"id": "fh-seed-001", "target": "fair-housing", "schema_version": 1, "direction": "input", "text": "", "context": {"prior_turns": [], "user_prompt": null}, "verdict": "block", "category": "", "secondary_categories": [], "guide_rule": "", "citations": [""], "rationale": "", "tags": [], "source": {"kind": "seed"}, "labels": {"provisional": "block"}, "created": "2026-09-24"}
```

Output seed:

```json
{"id": "fh-seed-002", "target": "fair-housing", "schema_version": 1, "direction": "output", "text": "", "context": {"prior_turns": [], "user_prompt": ""}, "verdict": "block", "category": "", "secondary_categories": [], "guide_rule": "", "citations": [""], "rationale": "", "tags": [], "source": {"kind": "seed"}, "labels": {"provisional": "block"}, "created": "2026-09-24"}
```

Allow seed (a hard negative):

```json
{"id": "fh-seed-003", "target": "fair-housing", "schema_version": 1, "direction": "input", "text": "", "context": {"prior_turns": [], "user_prompt": null}, "verdict": "allow", "category": "none", "secondary_categories": [], "guide_rule": null, "citations": [], "rationale": "Hard negative under FS-3: ", "tags": [], "source": {"kind": "seed"}, "labels": {"provisional": "allow"}, "created": "2026-09-24"}
```

## Check before committing

- The rule belongs to the category, its verdict matches the seed's verdict for the direction, and each citation is one the rule lists.
- `labels.provisional` equals `verdict`.
- The file validates: `uv run redline validate targets/fair-housing/seeds/*.jsonl`. CI runs the same check.

`redline validate` checks the record format. It does not yet check that the category, rule, and citations exist in `categories.yaml`, so the first bullet is on you for now.
