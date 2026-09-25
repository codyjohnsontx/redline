"""The judge interface: what every judge takes, what it returns, and how callers run it.

A judge reports failure in `Judgment.error` and never applies a fail policy itself;
the caller (the runtime or the eval runner) decides what an errored judgment means.
"""

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, NonNegativeInt, model_validator

from redline.datasets.schema import (
    NO_CATEGORY,
    VERDICTS_BY_DIRECTION,
    CategoryId,
    Context,
    Direction,
    Record,
    Verdict,
)

DEFAULT_CONCURRENCY = 8


def decision_problem(
    verdict: Verdict, category: str, direction: Direction | None = None
) -> str | None:
    """Why a judge's decision is inconsistent, or None when it is sound.

    `allow` goes with category `none` and every other verdict with a live category,
    so a decision can never score as a category hit while its verdict is wrong.
    With `direction`, the verdict must also be one that direction allows.
    """
    if direction is not None and verdict not in VERDICTS_BY_DIRECTION[direction]:
        return f"verdict {verdict!r} is not valid for direction {direction!r}"
    if verdict == "allow" and category != NO_CATEGORY:
        return f"verdict 'allow' requires category {NO_CATEGORY!r}, not {category!r}"
    if verdict != "allow" and category == NO_CATEGORY:
        return f"verdict {verdict!r} requires a category other than {NO_CATEGORY!r}"
    return None


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class JudgeInput(_Model):
    """What a judge sees: the text and its context, never the record's labels or id."""

    direction: Direction
    text: str
    context: Context = Field(default_factory=Context)
    target: str

    @classmethod
    def from_record(cls, record: Record) -> Self:
        return cls(
            direction=record.direction,
            text=record.text,
            context=record.context,
            target=record.target,
        )

    def key(self) -> str:
        """A stable content hash of this input, used to look up recorded judgments."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Usage(_Model):
    tokens_in: NonNegativeInt
    tokens_out: NonNegativeInt
    usd: float | None = None


class Judgment(_Model):
    """One judge decision. `verdict` and `category` are None exactly when `error` is set."""

    verdict: Verdict | None
    category: CategoryId | None
    rationale: str = ""
    # Only when the provider gives one; never invented.
    confidence: float | None = None
    judge_id: str
    latency_ms: NonNegativeInt = 0
    usage: Usage | None = None
    # Provider payload, kept for audit.
    raw: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    error: str | None = None

    @model_validator(mode="after")
    def _error_or_decision(self) -> Self:
        if self.error is None:
            if self.verdict is None or self.category is None:
                raise ValueError("a judgment without error requires verdict and category")
            problem = decision_problem(self.verdict, self.category)
            if problem is not None:
                raise ValueError(problem)
        elif self.verdict is not None or self.category is not None:
            raise ValueError("an errored judgment must not carry a verdict or category")
        return self

    @classmethod
    def failed(cls, judge_id: str, error: str, *, latency_ms: int = 0) -> Self:
        return cls(
            verdict=None, category=None, judge_id=judge_id, latency_ms=latency_ms, error=error
        )


class Judge(Protocol):
    # Stable across a run; includes whatever changes the judge's behaviour.
    @property
    def id(self) -> str: ...

    async def judge(self, item: JudgeInput) -> Judgment: ...

    async def judge_many(
        self, items: Sequence[JudgeInput], *, concurrency: int = DEFAULT_CONCURRENCY
    ) -> list[Judgment]: ...


class BaseJudge(ABC):
    """A judge that runs `judge_many` as `judge` calls with bounded concurrency."""

    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    async def judge(self, item: JudgeInput) -> Judgment: ...

    async def judge_many(
        self, items: Sequence[JudgeInput], *, concurrency: int = DEFAULT_CONCURRENCY
    ) -> list[Judgment]:
        if concurrency < 1:
            raise ValueError(f"concurrency must be at least 1, not {concurrency}")
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(item: JudgeInput) -> Judgment:
            async with semaphore:
                return await self.judge(item)

        return list(await asyncio.gather(*(bounded(item) for item in items)))
