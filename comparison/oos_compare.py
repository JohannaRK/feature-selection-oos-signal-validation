#!/usr/bin/env python3
"""Compare jo.* train/OOS rank IC metrics without third-party dependencies."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


PRED_RE = re.compile(r"^predictions_mr_(train|oos)_(\d+)\.csv$")
METRICS = {
    "blend": ("pred_blend", "target_blend"),
    "h6": ("pred_6", "O_6"),
    "h9": ("pred_9", "O_9"),
}
DELTA_PAIRS = [
    ("select2_minus_base", "select2", "base"),
    ("select_minus_base", "select", "base"),
    ("select_minus_select2", "select", "select2"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default="data",
        help="Directory containing jo.base, jo.select, jo.select2.",
    )
    parser.add_argument(
        "--runs",
        nargs="+",
        default=["jo.base", "jo.select", "jo.select2"],
        help="Run directory names to compare.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "oos"],
        choices=["train", "oos"],
        help="Splits to process.",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs_jo_compare",
        help="Directory where comparison outputs will be written.",
    )
    return parser.parse_args()


def run_label(run_name: str) -> str:
    return run_name[3:] if run_name.startswith("jo.") else run_name


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denom_x = math.sqrt(sum(x * x for x in dx))
    denom_y = math.sqrt(sum(y * y for y in dy))
    if denom_x == 0.0 or denom_y == 0.0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / (denom_x * denom_y)


def spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "std": None,
            "ci95_low": None,
            "ci95_high": None,
        }
    result: dict[str, float | int | None] = {
        "n": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
        "std": None,
        "ci95_low": None,
        "ci95_high": None,
    }
    if len(values) >= 2:
        mu = float(result["mean"])
        variance = sum((value - mu) ** 2 for value in values) / (len(values) - 1)
        std = math.sqrt(variance)
        half_width = 1.96 * std / math.sqrt(len(values))
        result["std"] = std
        result["ci95_low"] = mu - half_width
        result["ci95_high"] = mu + half_width
    return result


def fmt(value: object) -> object:
    if isinstance(value, float):
        return f"{value:.12g}"
    if value is None:
        return ""
    return value


def discover_prediction_files(run_dir: Path, splits: list[str]) -> dict[str, list[tuple[int, Path]]]:
    files: dict[str, list[tuple[int, Path]]] = {split: [] for split in splits}
    if not run_dir.is_dir():
        return files
    for entry in sorted(run_dir.iterdir(), key=lambda p: p.name):
        match = PRED_RE.match(entry.name)
        if not match:
            continue
        split, fold_text = match.group(1), match.group(2)
        if split in files:
            files[split].append((int(fold_text), entry))
    for split in files:
        files[split].sort(key=lambda item: item[0])
    return files


def process_prediction_file(
    path: Path,
    run_name: str,
    split: str,
    fold: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_date: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(
        lambda: {metric: [] for metric in METRICS}
    )
    n_rows = 0
    valid_pairs = {metric: 0 for metric in METRICS}

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [
            column
            for pair in METRICS.values()
            for column in pair
            if column not in (reader.fieldnames or [])
        ]
        if "date" not in (reader.fieldnames or []):
            missing_columns.append("date")
        if missing_columns:
            raise ValueError(f"{path} missing columns: {sorted(set(missing_columns))}")

        for row in reader:
            n_rows += 1
            date = row.get("date", "")
            if not date:
                continue
            for metric, (pred_col, target_col) in METRICS.items():
                pred = parse_float(row.get(pred_col))
                target = parse_float(row.get(target_col))
                if pred is None or target is None:
                    continue
                by_date[date][metric].append((pred, target))
                valid_pairs[metric] += 1

    date_rows: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []

    for metric in METRICS:
        date_ics = []
        for date in sorted(by_date):
            pairs = by_date[date][metric]
            ic = spearman(pairs)
            if ic is None:
                continue
            date_ics.append(ic)
            date_rows.append(
                {
                    "run": run_name,
                    "run_label": run_label(run_name),
                    "split": split,
                    "fold": fold,
                    "metric": metric,
                    "date": date,
                    "n_pairs": len(pairs),
                    "spearman_ic": ic,
                }
            )

        stats = summarize(date_ics)
        fold_rows.append(
            {
                "run": run_name,
                "run_label": run_label(run_name),
                "split": split,
                "fold": fold,
                "metric": metric,
                "n_rows": n_rows,
                "n_valid_pairs": valid_pairs[metric],
                "n_valid_dates": stats["n"],
                "mean_ic": stats["mean"],
                "median_ic": stats["median"],
                "min_ic": stats["min"],
                "max_ic": stats["max"],
            }
        )

    return fold_rows, date_rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: fmt(row.get(field)) for field in fieldnames})


def build_delta_rows(fold_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    values = {}
    for row in fold_rows:
        key = (row["split"], row["fold"], row["metric"], row["run_label"])
        values[key] = row["mean_ic"]

    split_folds_metrics = sorted({(row["split"], row["fold"], row["metric"]) for row in fold_rows})
    delta_rows = []
    for split, fold, metric in split_folds_metrics:
        for delta_name, left, right in DELTA_PAIRS:
            left_value = values.get((split, fold, metric, left))
            right_value = values.get((split, fold, metric, right))
            if left_value is None or right_value is None:
                continue
            delta_rows.append(
                {
                    "split": split,
                    "fold": fold,
                    "metric": metric,
                    "delta_name": delta_name,
                    "left_run": left,
                    "right_run": right,
                    "left_mean_ic": left_value,
                    "right_mean_ic": right_value,
                    "delta_mean_ic": float(left_value) - float(right_value),
                }
            )
    return delta_rows


def build_summary_by_run(fold_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object], list[float]] = defaultdict(list)
    for row in fold_rows:
        value = row["mean_ic"]
        if value is not None:
            grouped[(row["run"], row["split"], row["metric"])].append(float(value))

    rows = []
    for (run_name, split, metric), values in sorted(grouped.items()):
        stats = summarize(values)
        rows.append(
            {
                "run": run_name,
                "run_label": run_label(str(run_name)),
                "split": split,
                "metric": metric,
                "n_folds": stats["n"],
                "mean_fold_ic": stats["mean"],
                "median_fold_ic": stats["median"],
                "min_fold_ic": stats["min"],
                "max_fold_ic": stats["max"],
                "std_fold_ic": stats["std"],
                "ci95_low": stats["ci95_low"],
                "ci95_high": stats["ci95_high"],
            }
        )
    return rows


def build_delta_summary(delta_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object], list[float]] = defaultdict(list)
    for row in delta_rows:
        grouped[(row["split"], row["metric"], row["delta_name"])].append(float(row["delta_mean_ic"]))

    rows = []
    for (split, metric, delta_name), values in sorted(grouped.items()):
        stats = summarize(values)
        rows.append(
            {
                "split": split,
                "metric": metric,
                "delta_name": delta_name,
                "n_folds": stats["n"],
                "mean_delta": stats["mean"],
                "median_delta": stats["median"],
                "min_delta": stats["min"],
                "max_delta": stats["max"],
                "std_delta": stats["std"],
                "ci95_low": stats["ci95_low"],
                "ci95_high": stats["ci95_high"],
                "positive_folds": sum(1 for value in values if value > 0),
                "negative_folds": sum(1 for value in values if value < 0),
                "zero_folds": sum(1 for value in values if value == 0),
            }
        )
    return rows


def write_decision_summary(path: Path, summary_rows: list[dict[str, object]], delta_rows: list[dict[str, object]]) -> None:
    oos_blend = [
        row
        for row in summary_rows
        if row["split"] == "oos" and row["metric"] == "blend"
    ]
    oos_deltas = [
        row
        for row in delta_rows
        if row["split"] == "oos" and row["metric"] == "blend"
    ]

    lines = [
        "# Comparison Decision Summary",
        "",
        "Primary decision metric: OOS mean fold Spearman IC for `pred_blend` vs `target_blend`.",
        "",
        "This is a signal-quality comparison, not a full trading backtest.",
        "",
        "## OOS Blend by Run",
        "",
    ]

    if not oos_blend:
        lines.append("No OOS blend summary was available.")
    else:
        lines.append("| run | n_folds | mean_fold_ic | median_fold_ic | ci95_low | ci95_high |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in sorted(oos_blend, key=lambda item: str(item["run_label"])):
            lines.append(
                "| {run} | {n} | {mean_ic} | {median_ic} | {low} | {high} |".format(
                    run=row["run_label"],
                    n=fmt(row["n_folds"]),
                    mean_ic=fmt(row["mean_fold_ic"]),
                    median_ic=fmt(row["median_fold_ic"]),
                    low=fmt(row["ci95_low"]),
                    high=fmt(row["ci95_high"]),
                )
            )

    lines.extend(["", "## OOS Blend Deltas", ""])
    if not oos_deltas:
        lines.append("No paired OOS blend deltas were available.")
    else:
        lines.append("| delta | n_folds | mean_delta | median_delta | positive | negative | ci95_low | ci95_high |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in sorted(oos_deltas, key=lambda item: str(item["delta_name"])):
            lines.append(
                "| {name} | {n} | {mean_delta} | {median_delta} | {pos} | {neg} | {low} | {high} |".format(
                    name=row["delta_name"],
                    n=fmt(row["n_folds"]),
                    mean_delta=fmt(row["mean_delta"]),
                    median_delta=fmt(row["median_delta"]),
                    pos=fmt(row["positive_folds"]),
                    neg=fmt(row["negative_folds"]),
                    low=fmt(row["ci95_low"]),
                    high=fmt(row["ci95_high"]),
                )
            )

    lines.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "- `base > select2 > select`: feature removal probably removed useful signal.",
            "- `base ~ select2 > select`: `select2` is the likely compromise; `select` is too aggressive.",
            "- `select2 ~ base`: moderate reduction is acceptable if stability is good.",
            "- `select/select2 > base`: feature reduction likely removed noise.",
            "",
            "Follow-up work should only move to conditional PnL, freshness, and time-stop after this OOS comparison is reviewed.",
        ]
    )

    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    data_root = Path(args.data_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fold_rows: list[dict[str, object]] = []
    date_rows: list[dict[str, object]] = []
    warnings: list[str] = []

    for run_name in args.runs:
        run_dir = data_root / run_name
        if not run_dir.is_dir():
            warnings.append(f"missing run directory: {run_dir}")
            continue
        files = discover_prediction_files(run_dir, args.splits)
        for split in args.splits:
            if not files[split]:
                warnings.append(f"no {split} prediction files found in {run_dir}")
                continue
            for fold, path in files[split]:
                try:
                    fold_part, date_part = process_prediction_file(path, run_name, split, fold)
                except Exception as exc:  # noqa: BLE001 - keep going across folds.
                    warnings.append(f"failed to process {path}: {exc!r}")
                    continue
                fold_rows.extend(fold_part)
                date_rows.extend(date_part)

    delta_rows = build_delta_rows(fold_rows)
    summary_rows = build_summary_by_run(fold_rows)
    delta_summary_rows = build_delta_summary(delta_rows)

    write_csv(
        out_dir / "fold_metrics.csv",
        fold_rows,
        [
            "run",
            "run_label",
            "split",
            "fold",
            "metric",
            "n_rows",
            "n_valid_pairs",
            "n_valid_dates",
            "mean_ic",
            "median_ic",
            "min_ic",
            "max_ic",
        ],
    )
    write_csv(
        out_dir / "date_ic.csv",
        date_rows,
        ["run", "run_label", "split", "fold", "metric", "date", "n_pairs", "spearman_ic"],
    )
    write_csv(
        out_dir / "fold_deltas.csv",
        delta_rows,
        [
            "split",
            "fold",
            "metric",
            "delta_name",
            "left_run",
            "right_run",
            "left_mean_ic",
            "right_mean_ic",
            "delta_mean_ic",
        ],
    )
    write_csv(
        out_dir / "summary_by_run.csv",
        summary_rows,
        [
            "run",
            "run_label",
            "split",
            "metric",
            "n_folds",
            "mean_fold_ic",
            "median_fold_ic",
            "min_fold_ic",
            "max_fold_ic",
            "std_fold_ic",
            "ci95_low",
            "ci95_high",
        ],
    )
    write_csv(
        out_dir / "delta_summary.csv",
        delta_summary_rows,
        [
            "split",
            "metric",
            "delta_name",
            "n_folds",
            "mean_delta",
            "median_delta",
            "min_delta",
            "max_delta",
            "std_delta",
            "ci95_low",
            "ci95_high",
            "positive_folds",
            "negative_folds",
            "zero_folds",
        ],
    )
    write_decision_summary(out_dir / "decision_summary.md", summary_rows, delta_summary_rows)

    run_summary = {
        "data_root": str(data_root),
        "runs": args.runs,
        "splits": args.splits,
        "n_fold_metric_rows": len(fold_rows),
        "n_date_ic_rows": len(date_rows),
        "n_delta_rows": len(delta_rows),
        "warnings": warnings,
    }
    with (out_dir / "compare_run_summary.json").open("w") as handle:
        json.dump(run_summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Wrote outputs to {out_dir}")
    print(f"Fold metric rows: {len(fold_rows)}")
    print(f"Date IC rows: {len(date_rows)}")
    print(f"Delta rows: {len(delta_rows)}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
