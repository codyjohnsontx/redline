from pathlib import Path

import pytest

from redline.cli import main

from .conftest import SAMPLES, WriteRecords, sample_dicts


def test_validate_accepts_samples(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(SAMPLES)]) == 0
    assert "ok: 3 record(s) in 1 file(s)" in capsys.readouterr().out


def test_validate_rejects_bad_verdict_for_direction(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    records = sample_dicts()
    records[2]["verdict"] = "redirect"
    path = write_records(records)
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:3: verdict 'redirect' is not valid for direction 'output'" in err


def test_validate_reports_every_bad_line(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    records = sample_dicts()
    records[0]["direction"] = "sideways"
    records[2]["verdict"] = "redirect"
    path = write_records(records)
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:1: direction" in err
    assert f"{path}:3: " in err


def test_validate_rejects_malformed_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text('{"id": "fh-seed-001",\n', encoding="utf-8")
    assert main(["validate", str(path)]) == 1
    assert f"{path}:1: Invalid JSON" in capsys.readouterr().err


def test_validate_refuses_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(SAMPLES.parent / "does-not-exist.jsonl")]) == 2
    assert "not a file" in capsys.readouterr().err


def test_validate_rejects_duplicate_ids_across_files(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    first = write_records(sample_dicts())
    second = write_records(sample_dicts()[:1])
    assert main(["validate", str(first), str(second)]) == 1
    assert "duplicate id 'fh-seed-001'" in capsys.readouterr().err


def test_validate_rejects_family_split_across_files(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    seed, flip, _ = sample_dicts()
    flip["split"] = "val"
    assert main(["validate", str(write_records([seed])), str(write_records([flip]))]) == 1
    assert "family 'fh-seed-001' spans splits" in capsys.readouterr().err
