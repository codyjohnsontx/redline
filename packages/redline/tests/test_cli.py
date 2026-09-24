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


def test_validate_rejects_split_that_ignores_the_family_hash(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    seed, flip, _ = sample_dicts()
    seed["split"] = flip["split"] = "val"
    seed_path, flip_path = write_records([seed]), write_records([flip])
    assert main(["validate", str(seed_path), str(flip_path)]) == 1
    err = capsys.readouterr().err
    assert f"{seed_path}:1: split 'val' does not match 'train'" in err
    assert f"{flip_path}:1: split 'val' does not match 'train'" in err


def test_validate_rejects_parent_that_is_not_a_root_seed(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    seed, flip, _ = sample_dicts()
    synth = {**flip, "id": "fh-synth-001", "source": {"kind": "synth", "parent_id": "fh-seed-001"}}
    adversarial = {
        **flip,
        "id": "fh-adv-001",
        "source": {"kind": "adversarial", "parent_id": "fh-synth-001"},
        "split": None,
    }
    path = write_records([seed, synth, adversarial])
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:3: source.parent_id: 'fh-synth-001' is not a root seed" in err
    assert f"{path}:2:" not in err


def test_validate_rejects_parent_missing_from_the_files(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    _, flip, _ = sample_dicts()
    flip["source"]["parent_id"] = "fh-seed-01"  # typo for fh-seed-001
    flip["split"] = None
    path = write_records([flip])
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:1: source.parent_id: no valid record with id 'fh-seed-01'" in err


def test_validate_reports_invalid_utf8_per_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = SAMPLES.read_bytes().splitlines(keepends=True)
    path = tmp_path / "latin1.jsonl"
    path.write_bytes(lines[0] + b'{"text": "caf\xe9"}\n' + lines[1])
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:2: invalid UTF-8" in err
    assert f"{path}:1:" not in err
    assert f"{path}:3:" not in err


@pytest.mark.parametrize("parent_kind", ["hard_negative", "playground"])
def test_validate_rejects_parent_that_is_not_a_seed(
    parent_kind: str, write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    _, flip, _ = sample_dicts()
    parent = {
        **flip,
        "id": "fh-root-001",
        "source": {"kind": parent_kind},
        "labels": {"provisional": "allow"},
        "split": None,
    }
    child = {**flip, "source": {"kind": "synth", "parent_id": "fh-root-001"}, "split": None}
    path = write_records([parent, child])
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert f"{path}:2: source.parent_id: 'fh-root-001' is a {parent_kind!r} record" in err
    assert f"{path}:1:" not in err


def test_validate_rejects_variant_of_another_targets_seed(
    write_records: WriteRecords, capsys: pytest.CaptureFixture[str]
) -> None:
    seed, flip, _ = sample_dicts()
    flip["target"] = "race-engineer"
    path = write_records([seed, flip])
    assert main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert (
        f"{path}:2: target: 'race-engineer' does not match target 'fair-housing' "
        "of its seed 'fh-seed-001'" in err
    )
