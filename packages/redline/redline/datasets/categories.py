"""A target's categories.yaml: the category ids, guide rule ids, and citation strings records use.

Only the parts records point into are read; the rest of the file is the guide's data and
is left alone.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from redline.datasets.schema import CategoryId, NonEmpty, Slug, Verdict

CATEGORIES_FILE = "categories.yaml"


class CategoriesError(Exception):
    pass


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


class GuideRule(_Model):
    verdict: Verdict


class Category(_Model):
    rules: dict[NonEmpty, GuideRule]


class TargetCategories(_Model):
    target: Slug
    categories: dict[CategoryId, Category]
    citations: dict[NonEmpty, NonEmpty]


def categories_path(targets_dir: Path, target: str) -> Path:
    return targets_dir / target / CATEGORIES_FILE


def load_categories(targets_dir: Path, target: str) -> TargetCategories:
    """Read `targets_dir/<target>/categories.yaml`, raising CategoriesError if it is unusable."""
    path = categories_path(targets_dir, target)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CategoriesError(f"cannot read {path}: {exc.strerror or exc}") from exc
    except yaml.YAMLError as exc:
        raise CategoriesError(f"{path} is not valid YAML: {exc}") from exc
    try:
        categories = TargetCategories.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise CategoriesError(f"{path} is not a categories file: {problems}") from exc
    if categories.target != target:
        raise CategoriesError(f"{path} names target {categories.target!r}, not {target!r}")
    return categories
