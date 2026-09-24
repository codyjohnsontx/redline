import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

SAMPLES = Path(__file__).parent / "fixtures" / "samples.jsonl"

WriteRecords = Callable[[list[dict[str, Any]]], Path]


def sample_dicts() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def write_records(tmp_path: Path) -> WriteRecords:
    def write(records: list[dict[str, Any]]) -> Path:
        path = tmp_path / f"records-{len(list(tmp_path.iterdir()))}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    return write
