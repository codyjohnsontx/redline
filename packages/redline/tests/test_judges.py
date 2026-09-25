import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError

from redline.datasets.schema import Context
from redline.judges.base import BaseJudge, JudgeInput, Judgment
from redline.judges.keyword import KeywordJudge, KeywordRules
from redline.judges.recorded import RecordedJudge, RecordingError

EVAL_FIXTURES = Path(__file__).parent / "fixtures" / "eval"
KEYWORDS = EVAL_FIXTURES / "keywords.json"
RECORDING = EVAL_FIXTURES / "recording.jsonl"


def fixture_input(text: str, direction: str = "input") -> JudgeInput:
    context = (
        Context(user_prompt="Write a short listing for my unit.")
        if direction == "output"
        else Context()
    )
    return JudgeInput.model_validate(
        {"direction": direction, "text": text, "context": context, "target": "fixture"}
    )


def judge_one(judge: BaseJudge, item: JudgeInput) -> Judgment:
    return asyncio.run(judge.judge(item))


def test_keyword_judge_first_matching_rule_decides() -> None:
    judge = KeywordJudge.from_file(KEYWORDS)
    judgment = judge_one(judge, fixture_input("Alpha tenants only, beta too."))
    assert (judgment.verdict, judgment.category) == ("block", "alpha")
    assert judgment.raw == {"rule": "alpha-block", "pattern": r"\balpha\b"}
    assert judgment.judge_id == judge.id


def test_keyword_judge_allows_when_nothing_matches() -> None:
    judge = KeywordJudge.from_file(KEYWORDS)
    judgment = judge_one(judge, fixture_input("Which units have a big alphabet mural?"))
    assert (judgment.verdict, judgment.category, judgment.error) == ("allow", "none", None)


def test_keyword_judge_skips_rules_for_the_other_direction() -> None:
    rules = KeywordRules.model_validate_json(
        json.dumps(
            {
                "target": "fixture",
                "rules": [
                    {
                        "id": "r1",
                        "category": "alpha",
                        "verdict": "redirect",
                        "directions": ["input"],
                        "patterns": ["alpha"],
                    }
                ],
            }
        )
    )
    judge = KeywordJudge(rules)
    assert judge_one(judge, fixture_input("alpha")).verdict == "redirect"
    assert judge_one(judge, fixture_input("alpha", direction="output")).verdict == "allow"


def test_keyword_judge_reports_a_target_mismatch_as_an_error() -> None:
    judge = KeywordJudge.from_file(KEYWORDS)
    item = JudgeInput(direction="input", text="alpha", target="other")
    judgment = judge_one(judge, item)
    assert judgment.verdict is None
    assert judgment.error == "rules are for target 'fixture', not 'other'"


def test_keyword_judge_id_follows_the_rules() -> None:
    rules = KeywordRules.model_validate_json(KEYWORDS.read_bytes())
    changed = rules.model_copy(update={"rules": rules.rules[:1]})
    assert KeywordJudge(rules).id == KeywordJudge(rules).id
    assert KeywordJudge(rules).id != KeywordJudge(changed).id


@pytest.mark.parametrize(
    ("rule", "problem"),
    [
        ({"verdict": "redirect", "directions": ["output"]}, "not valid for direction 'output'"),
        ({"verdict": "allow"}, "other than allow"),
        ({"category": "none"}, "other than allow"),
        ({"patterns": ["("]}, "does not compile"),
        ({"patterns": []}, "at least 1 item"),
    ],
)
def test_keyword_rules_reject_bad_rules(rule: dict[str, object], problem: str) -> None:
    base: dict[str, object] = {
        "id": "r1",
        "category": "alpha",
        "verdict": "block",
        "directions": ["input", "output"],
        "patterns": ["alpha"],
    }
    with pytest.raises(ValidationError, match=problem):
        KeywordRules.model_validate_json(
            json.dumps({"target": "fixture", "rules": [{**base, **rule}]})
        )


def test_recorded_judge_replays_by_content() -> None:
    judge = RecordedJudge.from_file(RECORDING)
    judgment = judge_one(judge, fixture_input("Exclude everyone who is alpha."))
    assert (judgment.verdict, judgment.category, judgment.latency_ms) == ("redirect", "alpha", 200)
    assert judgment.judge_id == "fixture-judge"
    assert judge.id.startswith("recorded:recording@")


def test_recorded_judge_replays_recorded_errors() -> None:
    judge = RecordedJudge.from_file(RECORDING)
    judgment = judge_one(judge, fixture_input("Do not show beta renters anything."))
    assert (judgment.verdict, judgment.error) == (None, "timeout")


def test_recorded_judge_reports_a_missing_recording_as_an_error() -> None:
    judge = RecordedJudge.from_file(RECORDING)
    judgment = judge_one(judge, fixture_input("A text nobody recorded."))
    assert judgment.error == "no recorded judgment for this input"
    # Context is part of the match: the same text as output is a different input.
    other = judge_one(judge, fixture_input("Exclude everyone who is alpha.", direction="output"))
    assert other.error is not None


def test_recorded_judge_rejects_duplicate_and_invalid_recordings(tmp_path: Path) -> None:
    line = RECORDING.read_text(encoding="utf-8").splitlines()[0]
    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(RecordingError, match="two recordings for the same input"):
        RecordedJudge.from_file(duplicate)

    record = json.loads(line)
    record["judgment"]["error"] = "timeout"  # an error alongside a verdict
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(RecordingError, match=f"{invalid}:1:"):
        RecordedJudge.from_file(invalid)

    record["judgment"]["error"] = None
    record["input"]["direction"] = "output"  # redirect is input-only
    off_direction = tmp_path / "off_direction.jsonl"
    off_direction.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(RecordingError, match=f"(?s){off_direction}:1:.*not valid for direction"):
        RecordedJudge.from_file(off_direction)


class _SlowJudge(BaseJudge):
    def __init__(self) -> None:
        self.active = 0
        self.peak = 0

    @property
    def id(self) -> str:
        return "slow"

    async def judge(self, item: JudgeInput) -> Judgment:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.001)
        self.active -= 1
        return Judgment(verdict="allow", category="none", rationale=item.text, judge_id=self.id)


def test_judge_many_keeps_order_and_bounds_concurrency() -> None:
    judge = _SlowJudge()
    items: Sequence[JudgeInput] = [fixture_input(str(i)) for i in range(10)]
    judgments = asyncio.run(judge.judge_many(items, concurrency=3))
    assert [j.rationale for j in judgments] == [str(i) for i in range(10)]
    assert judge.peak == 3
