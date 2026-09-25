"""A regex baseline judge.

It gives the dashboard an honest floor and runs the metrics code with no network.
Its rules are data: a target's JSON rules file, never patterns written in Python.
"""

import hashlib
import re
import time
from pathlib import Path
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from redline.datasets.schema import (
    NO_CATEGORY,
    VERDICTS_BY_DIRECTION,
    CategoryId,
    Direction,
    Verdict,
)
from redline.judges.base import BaseJudge, JudgeInput, Judgment

NonEmpty = Annotated[str, StringConstraints(min_length=1)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class KeywordRule(_Model):
    id: NonEmpty
    category: CategoryId
    verdict: Verdict
    directions: list[Direction] = Field(min_length=1)
    # Python regular expressions, matched case-insensitively anywhere in the text.
    patterns: list[NonEmpty] = Field(min_length=1)

    @field_validator("patterns")
    @classmethod
    def _patterns_compile(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"pattern {pattern!r} does not compile: {exc}") from exc
        return patterns

    @model_validator(mode="after")
    def _decision_is_live(self) -> Self:
        if self.verdict == "allow" or self.category == NO_CATEGORY:
            raise ValueError("a keyword rule must name a category and a verdict other than allow")
        for direction in self.directions:
            if self.verdict not in VERDICTS_BY_DIRECTION[direction]:
                raise ValueError(
                    f"verdict {self.verdict!r} is not valid for direction {direction!r}"
                )
        return self


class KeywordRules(_Model):
    target: NonEmpty
    # Checked in order; the first rule with a matching pattern decides.
    rules: list[KeywordRule]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        seen: set[str] = set()
        for rule in self.rules:
            if rule.id in seen:
                raise ValueError(f"duplicate rule id {rule.id!r}")
            seen.add(rule.id)
        return self


class KeywordJudge(BaseJudge):
    def __init__(self, rules: KeywordRules, *, name: str = "keyword") -> None:
        self._rules = rules
        self._compiled = [
            (rule, [re.compile(p, re.IGNORECASE) for p in rule.patterns]) for rule in rules.rules
        ]
        digest = hashlib.sha256(rules.model_dump_json().encode("utf-8")).hexdigest()
        self._id = f"keyword:{name}@{digest[:12]}"

    @classmethod
    def from_file(cls, path: Path) -> Self:
        rules = KeywordRules.model_validate_json(path.read_bytes())
        return cls(rules, name=path.stem)

    @property
    def id(self) -> str:
        return self._id

    async def judge(self, item: JudgeInput) -> Judgment:
        if item.target != self._rules.target:
            return Judgment.failed(
                self._id,
                f"rules are for target {self._rules.target!r}, not {item.target!r}",
            )
        started = time.perf_counter()
        for rule, patterns in self._compiled:
            if item.direction not in rule.directions:
                continue
            for pattern in patterns:
                match = pattern.search(item.text)
                if match is not None:
                    return Judgment(
                        verdict=rule.verdict,
                        category=rule.category,
                        rationale=f"rule {rule.id} matched {match.group(0)!r}",
                        judge_id=self._id,
                        latency_ms=_elapsed_ms(started),
                        raw={"rule": rule.id, "pattern": pattern.pattern},
                    )
        return Judgment(
            verdict="allow",
            category=NO_CATEGORY,
            rationale="no rule matched",
            judge_id=self._id,
            latency_ms=_elapsed_ms(started),
        )


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
