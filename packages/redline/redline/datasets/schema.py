"""The dataset record: one JSON object per line in every Redline dataset file.

The rules here are the ones that hold for every target. Target-specific checks
(category ids, guide rule ids, citations) are data-driven and live elsewhere.
"""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Direction = Literal["input", "output"]
Verdict = Literal["allow", "redirect", "block"]
Split = Literal["train", "val", "test"]
SourceKind = Literal["seed", "synth", "flip", "hard_negative", "adversarial", "playground"]
GoldBasis = Literal["owner", "agreement"]

# On output a reply that correctly redirects is `allow`, so `redirect` is input-only.
VERDICTS_BY_DIRECTION: dict[Direction, frozenset[Verdict]] = {
    "input": frozenset({"allow", "redirect", "block"}),
    "output": frozenset({"allow", "block"}),
}

NO_CATEGORY = "none"

# Source kinds that are variants of a seed and so must name it as their parent.
DERIVED_KINDS: frozenset[SourceKind] = frozenset({"synth", "flip", "adversarial"})

RecordId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]*$")]
CategoryId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Turn(_Model):
    role: Literal["user", "assistant"]
    text: NonEmpty


class Context(_Model):
    prior_turns: list[Turn] = Field(default_factory=list[Turn])
    user_prompt: NonEmpty | None = None


class Source(_Model):
    kind: SourceKind
    parent_id: RecordId | None = None
    generator: NonEmpty | None = None
    generator_prompt_sha: NonEmpty | None = None
    transform: NonEmpty | None = None

    @model_validator(mode="after")
    def _parent_matches_kind(self) -> Self:
        if self.kind in DERIVED_KINDS and self.parent_id is None:
            raise ValueError(f"source.kind {self.kind!r} requires source.parent_id")
        if self.kind == "seed" and self.parent_id is not None:
            raise ValueError("source.kind 'seed' must not have a source.parent_id")
        return self


class SecondLabel(_Model):
    labeler: NonEmpty
    verdict: Verdict
    category: CategoryId


class OwnerLabel(_Model):
    verdict: Verdict
    category: CategoryId
    audited: date
    note: NonEmpty | None = None


class Labels(_Model):
    provisional: Verdict
    second: SecondLabel | None = None
    owner: OwnerLabel | None = None
    # None means the record is not gold yet: it stays in the audit queue.
    gold_basis: GoldBasis | None = None


class Record(_Model):
    id: RecordId
    target: Slug
    schema_version: Literal[1]
    direction: Direction
    text: NonEmpty
    context: Context = Field(default_factory=Context)
    verdict: Verdict
    category: CategoryId
    secondary_categories: list[CategoryId] = Field(default_factory=list[CategoryId])
    guide_rule: NonEmpty | None = None
    citations: list[NonEmpty] = Field(default_factory=list[NonEmpty])
    rationale: NonEmpty
    tags: list[NonEmpty] = Field(default_factory=list[NonEmpty])
    source: Source
    labels: Labels
    split: Split | None = None
    created: date

    @model_validator(mode="after")
    def _verdicts_fit_direction(self) -> Self:
        allowed = VERDICTS_BY_DIRECTION[self.direction]
        verdicts: list[tuple[str, Verdict]] = [
            ("verdict", self.verdict),
            ("labels.provisional", self.labels.provisional),
        ]
        if self.labels.second is not None:
            verdicts.append(("labels.second.verdict", self.labels.second.verdict))
        if self.labels.owner is not None:
            verdicts.append(("labels.owner.verdict", self.labels.owner.verdict))
        for field, verdict in verdicts:
            if verdict not in allowed:
                raise ValueError(
                    f"{field} {verdict!r} is not valid for direction {self.direction!r}; "
                    f"expected one of {sorted(allowed)}"
                )
        return self

    @model_validator(mode="after")
    def _context_fits_direction(self) -> Self:
        if self.direction == "output" and self.context.user_prompt is None:
            raise ValueError("direction 'output' requires context.user_prompt")
        if self.direction == "input" and self.context.user_prompt is not None:
            raise ValueError("direction 'input' must not set context.user_prompt")
        return self

    @model_validator(mode="after")
    def _category_fits_verdict(self) -> Self:
        if self.category == NO_CATEGORY:
            if self.verdict != "allow":
                raise ValueError(
                    f"category 'none' is only valid for verdict 'allow', not {self.verdict!r}"
                )
            if self.guide_rule is not None or self.citations:
                raise ValueError("category 'none' must not carry guide_rule or citations")
        else:
            if self.guide_rule is None or not self.citations:
                raise ValueError(f"category {self.category!r} requires guide_rule and citations")
        if NO_CATEGORY in self.secondary_categories or self.category in self.secondary_categories:
            raise ValueError("secondary_categories must not contain 'none' or the primary category")
        return self

    @model_validator(mode="after")
    def _gold_label_matches(self) -> Self:
        labels = self.labels
        if labels.gold_basis == "owner":
            if labels.owner is None:
                raise ValueError("labels.gold_basis 'owner' requires labels.owner")
            if (labels.owner.verdict, labels.owner.category) != (self.verdict, self.category):
                raise ValueError("verdict and category must match labels.owner")
        elif labels.gold_basis == "agreement":
            second = labels.second
            if second is None:
                raise ValueError("labels.gold_basis 'agreement' requires labels.second")
            if labels.provisional != second.verdict or second.category != self.category:
                raise ValueError(
                    "labels.gold_basis 'agreement' requires labels.provisional and "
                    "labels.second to agree with each other and with category"
                )
            if self.verdict != labels.provisional:
                raise ValueError("verdict must match the agreed label")
        if self.split in ("train", "val") and labels.gold_basis is None:
            raise ValueError(f"split {self.split!r} holds only gold records; set labels.gold_basis")
        return self
