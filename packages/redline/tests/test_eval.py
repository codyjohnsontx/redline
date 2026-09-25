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
import shutil
import time
from pathlib import Path

import pytest

from redline.cli import main
from redline.datasets.splits import assign_split
from redline.evaluate import load_metrics, run_eval
from redline.judges.base import BaseJudge, JudgeInput, Judgment, Usage
from redline.judges.recorded import RecordedJudge
from redline.metrics.report import DatasetInfo, ItemResult, compute_metrics, render_markdown

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
    # The one judge error, fx-in-09, is gold block, so none falls in the overblock basis.
    assert (overblock.error_rate.value, overblock.error_rate.n) == (0.0, 3)

    # Only fx-in-01 and fx-in-02 report usage, and only fx-in-01 has a price, so the
    # sums are partial and say so.
    cost = metrics.cost
    assert (cost.usd, cost.tokens_in, cost.tokens_out) == (0.001, 300, 30)
    assert (cost.items, cost.items_with_usage, cost.usage_with_price) == (14, 2, 1)
    assert cost.complete is False
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
    # The fixture records carry no split, so they hash as one unassigned group.
    assert run["dataset_sha256_by_split"] == {"unassigned": run["dataset_sha256"]}
    assert run["files"][0]["path"] == str(DATASET)
    assert (run["split"], run["n"]) == (None, 14)
    assert run["cost"]["complete"] is False


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
    assert (
        "- judge errors in the overblock basis, excluded from the overblock rate: "
        "0.000 [0.000, 0.561] (n 3); under the runtime's fail-closed output policy "
        "an output-direction error would reach the visitor as a refusal" in out
    )
    assert "- latency: p50 110 ms, p95 300 ms" in out
    assert (
        "- cost: partial, not a total: $0.0010 (price known for 1 of 2 usage records), "
        "300 tokens in, 30 tokens out (usage present for 2 of 14 items)" in out
    )
    assert "Average precision excludes" not in out


def test_run_file_hashes_each_split(tmp_path: Path) -> None:
    records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    # Every record but the last gets its family's split; the last stays unassigned.
    for record in records[:-1]:
        record["split"] = assign_split(record["id"])
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    judge = RecordedJudge.from_file(RECORDING)
    run = run_eval([dataset], judge, out_dir=tmp_path, run_id="all")
    by_split = json.loads((run.run_dir / "run.json").read_text())["dataset_sha256_by_split"]
    assert list(by_split) == ["test", "train", "unassigned", "val"]
    # Each split's hash is the dataset hash of a run over that split alone.
    for split in ("train", "val", "test"):
        alone = run_eval([dataset], judge, out_dir=tmp_path, split=split, run_id=split)
        assert by_split[split] == alone.metrics.dataset.sha256


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
    assert main(["report", str(tmp_path / "nothing")]) == 2
    assert "not a directory" in capsys.readouterr().err
    assert main(["report", str(tmp_path)]) == 1
    assert "missing run files" in capsys.readouterr().err


def split_runs(tmp_path: Path) -> tuple[Path, Path]:
    """Train and val runs over a copy of the fixtures with every record's split assigned."""
    records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    for record in records:
        record["split"] = assign_split(record["id"])
    dataset = tmp_path / "split.jsonl"
    dataset.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    judge = RecordedJudge.from_file(RECORDING)
    out = tmp_path / "results"
    train = run_eval([dataset], judge, out_dir=out, split="train", run_id="train")
    val = run_eval([dataset], judge, out_dir=out, split="val", run_id="val")
    return train.run_dir, val.run_dir


def test_report_accepts_a_consistent_split_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    train, _ = split_runs(tmp_path)
    assert main(["report", str(train)]) == 0
    assert "split train" in capsys.readouterr().out


def test_report_refuses_artifacts_from_different_splits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    train, val = split_runs(tmp_path)
    shutil.copy(val / "metrics.json", train / "metrics.json")
    assert main(["report", str(train)]) == 1
    err = capsys.readouterr().err
    assert "mixes artifacts that do not belong together" in err
    assert "split: run.json has 'train', metrics.json has 'val'" in err
    assert "metrics.json does not match" in err


def test_report_refuses_items_that_do_not_match_the_metrics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_recorded(tmp_path) == 0
    items = tmp_path / "run" / "items.jsonl"
    lines = items.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["predicted_verdict"], first["predicted_category"] = "allow", "none"
    items.write_text("\n".join([json.dumps(first), *lines[1:]]) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["report", str(tmp_path / "run")]) == 1
    assert "metrics.json does not match the 14 item(s)" in capsys.readouterr().err


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


class _HardNegativeErrorJudge(BaseJudge):
    """Replays the recording but errors on the hard negatives it recorded as allow."""

    def __init__(self) -> None:
        self._recorded = RecordedJudge.from_file(RECORDING)
        records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
        self._failing = {r["text"] for r in records if r["id"] in {"fx-in-06", "fx-out-03"}}

    @property
    def id(self) -> str:
        return "hard-negative-errors"

    async def judge(self, item: JudgeInput) -> Judgment:
        if item.text in self._failing:
            return Judgment.failed(self.id, "timeout")
        return await self._recorded.judge(item)


def test_overblock_rate_leaves_out_judge_errors_and_reports_them_beside_it(
    tmp_path: Path,
) -> None:
    run = run_eval([DATASET], _HardNegativeErrorJudge(), out_dir=tmp_path, run_id="run")
    overblock = run.metrics.rates.overblock_rate
    # Of the 3 hard negatives, 2 errored and the one judged (fx-in-07) was blocked.
    assert (overblock.value, overblock.n) == (1.0, 1)
    assert (overblock.error_rate.value, overblock.error_rate.n) == (pytest.approx(2 / 3), 3)
    # Every error, including the recorded fx-in-09 timeout, is still in judge_errors.
    assert run.metrics.rates.judge_errors == 3


class _BypassJudge(BaseJudge):
    """Returns an inconsistent decision built without validation, as a buggy judge might."""

    def __init__(self, verdict: str, category: str) -> None:
        self._verdict, self._category = verdict, category

    @property
    def id(self) -> str:
        return "bypass"

    async def judge(self, item: JudgeInput) -> Judgment:
        return Judgment.model_construct(
            verdict=self._verdict,
            category=self._category,
            rationale="",
            confidence=None,
            judge_id=self.id,
            latency_ms=0,
            usage=None,
            raw={},
            error=None,
        )


def first_record(tmp_path: Path) -> Path:
    """fx-in-01 alone: gold redirect alpha."""
    dataset = tmp_path / "one.jsonl"
    dataset.write_text(DATASET.read_text(encoding="utf-8").splitlines()[0] + "\n", "utf-8")
    return dataset


def test_recorded_allow_with_a_category_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The review's reproduction: record fx-in-01 (gold redirect alpha) as allow alpha.
    line = json.loads(RECORDING.read_text(encoding="utf-8").splitlines()[0])
    line["judgment"]["verdict"] = "allow"
    recording = tmp_path / "allow-alpha.jsonl"
    recording.write_text(json.dumps(line) + "\n", encoding="utf-8")
    args = ["eval", str(first_record(tmp_path)), "--judge", "recorded", "--recording"]
    assert main([*args, str(recording), "--out", str(tmp_path)]) == 1
    assert "verdict 'allow' requires category 'none', not 'alpha'" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("verdict", "category", "problem"),
    [
        ("allow", "alpha", "verdict 'allow' requires category 'none', not 'alpha'"),
        ("block", "none", "verdict 'block' requires a category other than 'none'"),
    ],
)
def test_an_inconsistent_decision_that_bypasses_validation_is_a_judge_error(
    tmp_path: Path, verdict: str, category: str, problem: str
) -> None:
    run = run_eval(
        [first_record(tmp_path)], _BypassJudge(verdict, category), out_dir=tmp_path, run_id="run"
    )
    alpha = run.metrics.per_category["alpha"]
    assert (alpha.tp, alpha.fn, alpha.recall, alpha.f1) == (0, 1, 0.0, 0.0)
    assert run.metrics.rates.judge_errors == 1
    item = json.loads((run.run_dir / "items.jsonl").read_text(encoding="utf-8"))
    assert (item["predicted_verdict"], item["predicted_category"]) == (None, None)
    assert item["error"] == problem


class _PricedJudge(BaseJudge):
    """Replays the recording with full usage and price on every judgment."""

    def __init__(self) -> None:
        self._recorded = RecordedJudge.from_file(RECORDING)

    @property
    def id(self) -> str:
        return "priced"

    async def judge(self, item: JudgeInput) -> Judgment:
        judgment = await self._recorded.judge(item)
        usage = Usage(tokens_in=10, tokens_out=2, usd=0.0005)
        return judgment.model_copy(update={"usage": usage})


def test_cost_is_a_total_only_when_every_item_is_priced(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = run_eval([DATASET], _PricedJudge(), out_dir=tmp_path, run_id="run")
    cost = run.metrics.cost
    assert cost.complete is True
    assert (cost.usd, cost.tokens_in, cost.tokens_out) == (pytest.approx(0.007), 140, 28)
    assert main(["report", str(run.run_dir)]) == 0
    assert "- cost: $0.0070, 140 tokens in, 28 tokens out\n" in capsys.readouterr().out


def test_keyword_run_reports_cost_as_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["eval", str(DATASET), "--judge", "keyword", "--rules", str(KEYWORDS)]
    assert main([*args, "--out", str(tmp_path), "--run-id", "kw"]) == 0
    capsys.readouterr()
    assert main(["report", str(tmp_path / "kw")]) == 0
    assert "- cost: unknown, no item reported usage" in capsys.readouterr().out


def test_report_says_how_many_categories_average_precision_excludes() -> None:
    def item(id: str, gold: str, predicted: str) -> ItemResult:
        return ItemResult(
            id=id,
            direction="input",
            source_kind="seed",
            gold_verdict="block",
            gold_category=gold,
            predicted_verdict="allow" if predicted == "none" else "block",
            predicted_category=predicted,
            error=None,
            judge_id="j",
            latency_ms=0,
            usage=None,
        )

    items = [item("a", "alpha", "alpha"), item("d", "delta", "none")]
    dataset = DatasetInfo(
        split=None, sha256="0" * 64, n=2, n_by_direction={"input": 2}, n_excluded_not_gold=0
    )
    metrics = compute_metrics(run_id="r", target="t", judge_id="j", dataset=dataset, items=items)
    out = render_markdown(metrics)
    assert "| delta | 1 | - |" in out
    assert "| macro | 1.000 | 0.500 | 0.500 |" in out
    assert (
        "Average precision excludes 1 category never predicted, whose precision is "
        "undefined; recall and F1 average over every category." in out
    )
