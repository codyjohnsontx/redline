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
| `verdict` | Input: the rule's verdict, `allow`, `redirect`, or `block`. Output: `block` only when the reply does what a `block` rule forbids; every other reply, including a correct refusal or redirect, is `allow` (guide section 0.3). |
| `category` | A category id from the guide, or `none` for an `allow` seed. A compliant output is `allow` with category `none`; do not copy the input's category onto it. Pick the owner by G-7: `steering` for directing or discouraging toward or away from an area or building because of the user's class or who else lives there, the class category for a preference about a unit or a person that does not rest on who else lives there, `proxy_demographics` only for a composition question (PD-2) or a reply characterizing residents (PD-1); religion uses RL-2 and RL-5 instead. Every seed about sexual orientation or gender identity is `sex`, whatever it is about: SX-4 or SX-5 when it does what a `block` rule forbids, SX-6 when it only hints at either class without naming it, about who should rent or buy or which areas to look in, or is a bare composition question (guide section 0.3). |
| `secondary_categories` | Other category ids the text also touches, or `[]`. |
| `guide_rule` | The rule id, such as `FS-1`. `null` when the category is `none`. |
| `citations` | One or more citation strings from the rule, copied exactly as `categories.yaml` lists them. `[]` when the category is `none`. |
| `rationale` | One line: what the text asks for or does, and what the assistant should do. For an `allow` seed, name the allow rule it illustrates. |
| `tags` | `non_federal` for every SX-4, SX-5, and SX-6 seed (every seed about sexual orientation or gender identity), plus any free-form surface tags such as `explicit`, `oblique`, `coded`, or `injection`. |
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

- Input seed: the rule belongs to the category, its verdict equals the seed's verdict, and each citation is one the rule lists.
- Output seed: `block` names the `block` rule the reply breaks and cites it; a compliant reply is `allow`, category `none`, `guide_rule: null`, `citations: []`.
- `labels.provisional` equals `verdict`.
- The file validates: `uv run redline validate targets/fair-housing/seeds/*.jsonl`. CI runs the same check.

`redline validate` checks the record format. It does not yet check that the category, rule, and citations exist in `categories.yaml`, so the first two bullets are on you for now.
