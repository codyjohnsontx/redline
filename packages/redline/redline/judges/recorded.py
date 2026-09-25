"""A judge that replays judgments from a recording file, for offline tests and CI.

A recording is JSONL, one `{"input": JudgeInput, "judgment": Judgment}` object per
line. Inputs are matched by content, so a recording does not depend on record ids.
"""

import hashlib
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, ValidationError

from redline.judges.base import BaseJudge, JudgeInput, Judgment


class Recording(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    input: JudgeInput
    judgment: Judgment


class RecordingError(Exception):
    pass


class RecordedJudge(BaseJudge):
    def __init__(self, recordings: list[Recording], *, id: str) -> None:
        self._id = id
        self._by_key: dict[str, Judgment] = {}
        for recording in recordings:
            key = recording.input.key()
            if key in self._by_key:
                raise RecordingError(f"two recordings for the same input: {recording.input.text!r}")
            self._by_key[key] = recording.judgment

    @classmethod
    def from_file(cls, path: Path) -> Self:
        data = path.read_bytes()
        recordings: list[Recording] = []
        for line_no, line in enumerate(data.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                recordings.append(Recording.model_validate_json(line))
            except ValidationError as exc:
                raise RecordingError(f"{path}:{line_no}: {exc}") from exc
        digest = hashlib.sha256(data).hexdigest()
        return cls(recordings, id=f"recorded:{path.stem}@{digest[:12]}")

    @property
    def id(self) -> str:
        return self._id

    async def judge(self, item: JudgeInput) -> Judgment:
        judgment = self._by_key.get(item.key())
        if judgment is None:
            return Judgment.failed(self._id, "no recorded judgment for this input")
        return judgment
