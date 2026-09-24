"""Read JSONL dataset files into validated records."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from redline.datasets.schema import Record


@dataclass(frozen=True)
class RecordError:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


@dataclass(frozen=True)
class LoadedRecord:
    path: Path
    line: int
    record: Record


@dataclass
class ParsedFile:
    path: Path
    records: list[LoadedRecord] = field(default_factory=list[LoadedRecord])
    errors: list[RecordError] = field(default_factory=list[RecordError])


class DatasetError(Exception):
    def __init__(self, errors: list[RecordError]) -> None:
        self.errors = errors
        super().__init__("\n".join(str(e) for e in errors))


def parse_jsonl(path: Path) -> ParsedFile:
    """Parse every line of `path`, collecting records and errors rather than stopping at one."""
    parsed = ParsedFile(path)
    with path.open("rb") as handle:
        for line_no, raw in enumerate(handle, start=1):
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                parsed.errors.append(RecordError(path, line_no, f"invalid UTF-8: {exc.reason}"))
                continue
            if not line.strip():
                continue
            try:
                record = Record.model_validate_json(line)
            except ValidationError as exc:
                parsed.errors.extend(
                    RecordError(path, line_no, _format_error(err)) for err in exc.errors()
                )
                continue
            parsed.records.append(LoadedRecord(path, line_no, record))
    return parsed


def load_records(path: Path) -> list[Record]:
    """Load a dataset file, raising DatasetError if any line is invalid."""
    parsed = parse_jsonl(path)
    if parsed.errors:
        raise DatasetError(parsed.errors)
    return [loaded.record for loaded in parsed.records]


def _format_error(err: ErrorDetails) -> str:
    loc = ".".join(str(part) for part in err["loc"])
    # Our own model validators raise ValueError; drop pydantic's "Value error, " prefix.
    ctx = err.get("ctx") or {}
    msg = str(ctx["error"]) if err["type"] == "value_error" and "error" in ctx else err["msg"]
    return f"{loc}: {msg}" if loc else msg
