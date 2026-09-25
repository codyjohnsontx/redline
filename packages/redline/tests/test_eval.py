"""`redline eval` and `redline report` over the hand-made fixtures.

tests/fixtures/eval/dataset.jsonl holds 14 gold records of a fixture target with
categories alpha and beta; recording.jsonl holds one judgment per record, one of
them an error. By hand, per record (gold -> recorded):

    fx-in-01   input   redirect alpha -> redirect alpha
    fx-in-02   input   block alpha    -> block alpha
    fx-in-03   input   block alpha    -> redirect alpha
    fx-in-04   input   block beta     -> block beta
    fx-in-05   input   redirect beta  -> allow none
    fx-in-06   input   allow none     -> allow none      hard negative
    fx-in-07   input   allow none     -> block beta      hard negative
    fx-in-08   input   allow none     -> allow none
    fx-in-09   input   block beta     -> error
    fx-out-01  output  block alpha    -> block alpha
    fx-out-02  output  block beta     -> block alpha
    fx-out-03  output  allow none     -> allow none      hard negative
    fx-out-04  output  allow none     -> block alpha
    fx-in-10   input   block alpha    -> block alpha

alpha: gold 5, predicted 7, TP 5, FP 2 (fx-out-02, fx-out-04), FN 0.
beta:  gold 4, predicted 2, TP 1, FP 1 (fx-in-07), FN 3 (fx-in-05, fx-in-09, fx-out-02).
"""

import json
import time
from pathlib import Path

import pytest

from redline.cli import main
from redline.evaluate import load_metrics, run_eval
from redline.judges.base import BaseJudge, JudgeInput, Judgment

from .conftest import SAMPLES

EVAL_FIXTURES = Path(__file__).parent / "fixtures" / "eval"
DATASET = EVAL_FIXTURES / "dataset.jsonl"
RECORDING = EVAL_FIXTURES / "recording.jsonl"
KEYWORDS = EVAL_FIXTURES / "keywords.json"


def run_recorded(out: Path, *extra: str) -> int:
    return main(
        [
            "eval",
            str(DATASET),
            "--judge",
            "recorded",
            "--recording",
            str(RECORDING),
            "--out",
            str(out),
            "--run-id",
            "run",
            *extra,
        ]
    )


def test_recorded_eval_matches_hand_computed_metrics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    started = time.perf_counter()
    assert run_recorded(tmp_path) == 0
    assert time.perf_counter() - started < 10
    assert "n 14, macro F1 0.583, judge errors 1" in capsys.readouterr().out

    metrics = load_metrics(tmp_path / "run")
    assert metrics.target == "fixture"
    assert metrics.dataset.n == 14
    assert metrics.dataset.n_by_direction == {"input": 10, "output": 4}

    confusion_in = metrics.verdict_confusion["input"]
    assert confusion_in.labels == ["allow", "redirect", "block"]
    assert confusion_in.matrix == [[2, 0, 1], [1, 1, 0], [0, 1, 3]]
    assert confusion_in.errors == [0, 0, 1]
    confusion_out = metrics.verdict_confusion["output"]
    assert confusion_out.labels == ["allow", "block"]
    assert confusion_out.matrix == [[1, 1], [0, 2]]
    assert confusion_out.errors == [0, 0]

    alpha, beta = metrics.per_category["alpha"], metrics.per_category["beta"]
    assert list(metrics.per_category) == ["alpha", "beta"]
    assert (alpha.n, alpha.tp, alpha.fp, alpha.fn) == (5, 5, 2, 0)
    assert alpha.precision == pytest.approx(5 / 7)
    assert alpha.recall == pytest.approx(1.0)
    assert alpha.f1 == pytest.approx(5 / 6)
    assert (beta.n, beta.tp, beta.fp, beta.fn) == (4, 1, 1, 3)
    assert beta.precision == pytest.approx(1 / 2)
    assert beta.recall == pytest.approx(1 / 4)
    assert beta.f1 == pytest.approx(1 / 3)

    # Wilson 95 percent intervals, hand-computed: 5 of 5 and 1 of 4.
    assert alpha.recall_ci95 == pytest.approx((0.5655, 1.0), abs=1e-4)
    assert beta.recall_ci95 == pytest.approx((0.0456, 0.6994), abs=1e-4)
    # Block recall: alpha 3 of 4 (fx-in-03 was redirected); beta 2 of 3, since
    # fx-out-02 was blocked under the wrong category and fx-in-09 errored.
    assert (alpha.n_block, alpha.block_recall) == (4, 0.75)
    assert alpha.block_recall_ci95 == pytest.approx((0.3006, 0.9544), abs=1e-4)
    assert beta.n_block == 3
    assert beta.block_recall == pytest.approx(2 / 3)
    assert beta.block_recall_ci95 == pytest.approx((0.2077, 0.9385), abs=1e-4)

    assert metrics.macro is not None and metrics.weighted is not None
    assert metrics.macro.precision == pytest.approx((5 / 7 + 1 / 2) / 2)
    assert metrics.macro.recall == pytest.approx((1 + 1 / 4) / 2)
    assert metrics.macro.f1 == pytest.approx((5 / 6 + 1 / 3) / 2)
    assert metrics.weighted.precision == pytest.approx((5 * 5 / 7 + 4 * 1 / 2) / 9)
    assert metrics.weighted.recall == pytest.approx((5 * 1 + 4 * 1 / 4) / 9)
    assert metrics.weighted.f1 == pytest.approx((5 * 5 / 6 + 4 * 1 / 3) / 9)

    rates = metrics.rates
    assert rates.judge_errors == 1
    # 7 blocks among the 13 judged items; 2 redirects among the 9 judged inputs.
    assert (rates.block_rate.value, rates.block_rate.n) == (pytest.approx(7 / 13), 13)
    assert (rates.redirect_rate.value, rates.redirect_rate.n) == (pytest.approx(2 / 9), 9)
    # Hard negatives fx-in-06, fx-in-07, fx-out-03; only fx-in-07 was blocked.
    overblock = rates.overblock_rate
    assert (overblock.value, overblock.n) == (pytest.approx(1 / 3), 3)
    assert overblock.ci95 == pytest.approx((0.0615, 0.7923), abs=1e-4)
    assert overblock.basis == "hard_negative+playground"

    assert metrics.cost is not None
    assert (metrics.cost.usd, metrics.cost.tokens_in, metrics.cost.tokens_out) == (0.001, 300, 30)
    # Nearest rank over the 13 judged latencies; the errored item's 5000 ms is left out.
    assert (metrics.latency_ms.p50, metrics.latency_ms.p95) == (110, 300)


def test_eval_writes_items_and_run_files(tmp_path: Path) -> None:
    assert run_recorded(tmp_path) == 0
    run_dir = tmp_path / "run"
    items = [json.loads(line) for line in (run_dir / "items.jsonl").read_text().splitlines()]
    assert [i["id"] for i in items][:2] == ["fx-in-01", "fx-in-02"]
    errored = next(i for i in items if i["id"] == "fx-in-09")
    assert errored["predicted_verdict"] is None and errored["error"] == "timeout"
    run = json.loads((run_dir / "run.json").read_text())
    assert run["judge_id"].startswith("recorded:recording@")
    assert run["dataset_sha256"] == load_metrics(run_dir).dataset.sha256
    assert run["files"][0]["path"] == str(DATASET)


def test_keyword_eval_over_the_fixtures(tmp_path: Path) -> None:
    # The keyword rules catch every alpha and beta word but also block the hard
    # negative "beta release": beta has TP 4, FP 1, so F1 8/9 and macro F1 17/18.
    args = ["eval", str(DATASET), "--judge", "keyword", "--rules", str(KEYWORDS)]
    assert main([*args, "--out", str(tmp_path), "--run-id", "kw"]) == 0
    metrics = load_metrics(tmp_path / "kw")
    assert metrics.rates.judge_errors == 0
    assert metrics.per_category["alpha"].f1 == pytest.approx(1.0)
    assert metrics.per_category["beta"].f1 == pytest.approx(8 / 9)
    assert metrics.macro is not None
    assert metrics.macro.f1 == pytest.approx(17 / 18)
    assert metrics.judge_id.startswith("keyword:keywords@")


def test_report_renders_the_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_recorded(tmp_path) == 0
    capsys.readouterr()
    assert main(["report", str(tmp_path / "run")]) == 0
    out = capsys.readouterr().out
    assert "| macro | 0.607 | 0.625 | 0.583 |" in out
    assert (
        "| alpha | 5 | 0.714 | 1.000 [0.566, 1.000] | 0.833 | 0.750 [0.301, 0.954] (n 4) |" in out
    )
    assert "| block | 0 | 1 | 3 | 1 |" in out
    assert "- overblock rate (hard_negative+playground): 0.333 [0.061, 0.792] (n 3)" in out
    assert "- latency: p50 110 ms, p95 300 ms" in out


def test_eval_filters_by_split(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # The fixture records carry no split, so a split filter leaves nothing to judge.
    assert run_recorded(tmp_path, "--split", "val") == 1
    assert "no gold records to evaluate in split val" in capsys.readouterr().err


def test_eval_excludes_records_that_are_not_gold(tmp_path: Path) -> None:
    lines = DATASET.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["labels"] = {"provisional": record["verdict"]}
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text("\n".join([json.dumps(record), *lines[1:]]) + "\n", encoding="utf-8")
    args = ["eval", str(dataset), "--judge", "recorded", "--recording", str(RECORDING)]
    assert main([*args, "--out", str(tmp_path), "--run-id", "run"]) == 0
    metrics = load_metrics(tmp_path / "run")
    assert (metrics.dataset.n, metrics.dataset.n_excluded_not_gold) == (13, 1)


def test_eval_refuses_mixed_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["eval", str(DATASET), str(SAMPLES), "--judge", "recorded", "--recording"]
    assert main([*args, str(RECORDING), "--out", str(tmp_path)]) == 1
    assert "records span several targets ['fair-housing', 'fixture']" in capsys.readouterr().err


def test_eval_refuses_an_existing_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_recorded(tmp_path) == 0
    assert run_recorded(tmp_path) == 1
    assert "already exists" in capsys.readouterr().err


def test_eval_requires_the_judge_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", str(DATASET), "--judge", "keyword"]) == 2
    assert "--judge keyword requires --rules" in capsys.readouterr().err


def test_eval_rejects_an_invalid_dataset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text('{"id": "x"}\n', encoding="utf-8")
    args = ["eval", str(dataset), "--judge", "keyword", "--rules", str(KEYWORDS)]
    assert main([*args, "--out", str(tmp_path)]) == 1
    assert f"{dataset}:1: " in capsys.readouterr().err


def test_report_refuses_a_missing_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", str(tmp_path)]) == 2
    assert "metrics.json: not a file" in capsys.readouterr().err


class _RedirectJudge(BaseJudge):
    @property
    def id(self) -> str:
        return "redirect"

    async def judge(self, item: JudgeInput) -> Judgment:
        return Judgment(verdict="redirect", category="alpha", judge_id=self.id)


def test_eval_counts_a_verdict_invalid_for_its_direction_as_a_judge_error(
    tmp_path: Path,
) -> None:
    run = run_eval([DATASET], _RedirectJudge(), out_dir=tmp_path, run_id="run")
    n_output = run.metrics.dataset.n_by_direction["output"]
    assert n_output > 0
    assert run.metrics.rates.judge_errors == n_output
    items = [
        json.loads(line)
        for line in (run.run_dir / "items.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    outputs = [i for i in items if i["direction"] == "output"]
    assert all(i["predicted_verdict"] is None and i["predicted_category"] is None for i in outputs)
    assert {i["error"] for i in outputs} == {
        "verdict 'redirect' is not valid for direction 'output'"
    }
