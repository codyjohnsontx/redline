"""The Fair Housing keyword rules: they load, point at real guide rules, and run an eval.

targets/fair-housing/keywords.json is built from Appendix B of the label guide. Each
keyword rule's id is the guide rule it applies, so it must name a rule under its
category in categories.yaml and carry that rule's input verdict.
"""

import json
import re
from pathlib import Path

from redline.cli import main
from redline.evaluate import load_metrics
from redline.judges.keyword import KeywordRules

TARGET = Path(__file__).parents[3] / "targets" / "fair-housing"
KEYWORDS = TARGET / "keywords.json"
CATEGORIES = TARGET / "categories.yaml"
SEEDS = TARGET / "seeds" / "examples.jsonl"


def guide_rule_verdicts() -> dict[str, dict[str, str]]:
    """Read `category -> rule id -> verdict` from the `categories:` block of categories.yaml.

    The engine has no YAML dependency, so this reads the file's fixed layout: category ids
    at two spaces, rule ids at six, and each rule's `verdict:` at eight.
    """
    categories: dict[str, dict[str, str]] = {}
    category = rule = None
    in_block = False
    for line in CATEGORIES.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            in_block = line == "categories:"
            continue
        if not in_block:
            continue
        if m := re.fullmatch(r"  ([a-z_]+):", line):
            category, rule = m.group(1), None
            categories[category] = {}
        elif m := re.fullmatch(r"      ([A-Z]{2}-\d+):", line):
            rule = m.group(1)
        elif (m := re.fullmatch(r"        verdict: (\w+)", line)) and category and rule:
            categories[category][rule] = m.group(1)
    return categories


def test_guide_rule_reader_sees_every_category() -> None:
    categories = guide_rule_verdicts()
    assert len(categories) == 12
    assert categories["race_color"]["RC-1"] == "block"
    assert categories["advertising_language"]["AD-2"] == "redirect"


def test_every_keyword_rule_names_a_guide_rule_in_its_category() -> None:
    rules = KeywordRules.model_validate_json(KEYWORDS.read_bytes())
    assert rules.target == "fair-housing"
    assert rules.rules
    categories = guide_rule_verdicts()
    for rule in rules.rules:
        assert rule.category in categories, f"{rule.id}: unknown category {rule.category!r}"
        guide_rules = categories[rule.category]
        assert rule.id in guide_rules, f"{rule.id}: no such rule under {rule.category!r}"
        assert rule.verdict == guide_rules[rule.id], f"{rule.id}: verdict differs from the guide"


def test_keyword_eval_over_the_example_seeds(tmp_path: Path) -> None:
    # The seeds are not gold yet and eval scores only gold records, so this copy marks
    # each one gold by agreement with itself. It checks that the run completes, not
    # that the labels are audited.
    records: list[dict[str, object]] = []
    for line in SEEDS.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        record["labels"] = {
            "provisional": record["verdict"],
            "second": {
                "labeler": "smoke-test",
                "verdict": record["verdict"],
                "category": record["category"],
            },
            "gold_basis": "agreement",
        }
        records.append(record)
    assert len(records) == 12
    dataset = tmp_path / "examples.jsonl"
    dataset.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    args = ["eval", str(dataset), "--judge", "keyword", "--rules", str(KEYWORDS)]
    assert main([*args, "--out", str(tmp_path / "results"), "--run-id", "fh"]) == 0
    metrics = load_metrics(tmp_path / "results" / "fh")
    assert metrics.target == "fair-housing"
    assert metrics.dataset.n == 12
    assert metrics.rates.judge_errors == 0
    assert metrics.judge_id.startswith("keyword:keywords@")
    assert main(["report", str(tmp_path / "results" / "fh")]) == 0
