#!/usr/bin/env python3
"""Inspect jo.* remote run folders without third-party dependencies."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


PRED_RE = re.compile(r"^predictions_mr_(train|oos)_(\d+)\.csv$")
METRICS_RE = re.compile(r"^predictions_mr_(train|oos)_(\d+)_metrics\.json$")
INTERESTING_RE = re.compile(
    r"(ranking|LS|cluster|distance|peer|volat|disp|perimeter|scaler|feature)",
    re.IGNORECASE,
)


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
        help="Run directory names to inspect.",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs_jo_compare",
        help="Directory where inspection_summary.json will be written.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=3,
        help="Number of sample rows to capture from the first CSV per split.",
    )
    return parser.parse_args()


def read_csv_preview(path: Path, sample_rows: int) -> dict:
    preview = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "columns": [],
        "sample_rows": [],
        "error": None,
    }
    if not path.exists():
        return preview
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            preview["columns"] = list(reader.fieldnames or [])
            for i, row in enumerate(reader):
                if i >= sample_rows:
                    break
                preview["sample_rows"].append(dict(row))
    except Exception as exc:  # noqa: BLE001 - inspection should report and continue.
        preview["error"] = repr(exc)
    return preview


def read_metrics_preview(path: Path) -> dict:
    preview = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "keys": [],
        "values": {},
        "error": None,
    }
    if not path.exists():
        return preview
    try:
        with path.open() as handle:
            data = json.load(handle)
        preview["keys"] = sorted(data.keys())
        preview["values"] = data
    except Exception as exc:  # noqa: BLE001 - inspection should report and continue.
        preview["error"] = repr(exc)
    return preview


def inspect_run(data_root: Path, run: str, sample_rows: int) -> dict:
    run_dir = data_root / run
    info = {
        "run": run,
        "path": str(run_dir),
        "exists": run_dir.exists(),
        "is_dir": run_dir.is_dir(),
        "top_level_file_count": 0,
        "top_level_dir_count": 0,
        "prediction_folds": {"train": [], "oos": []},
        "metrics_folds": {"train": [], "oos": []},
        "missing_metrics_for_predictions": {"train": [], "oos": []},
        "ls_dirs": [],
        "interesting_entries": [],
        "csv_previews": {},
        "metrics_previews": {},
        "errors": [],
    }
    if not run_dir.is_dir():
        return info

    try:
        entries = sorted(run_dir.iterdir(), key=lambda p: p.name)
    except Exception as exc:  # noqa: BLE001
        info["errors"].append(f"cannot list run directory: {exc!r}")
        return info

    for entry in entries:
        if entry.is_dir():
            info["top_level_dir_count"] += 1
            if entry.name.startswith("LS"):
                info["ls_dirs"].append(entry.name)
        elif entry.is_file():
            info["top_level_file_count"] += 1

        if INTERESTING_RE.search(entry.name):
            info["interesting_entries"].append(entry.name)

        pred_match = PRED_RE.match(entry.name)
        if pred_match:
            split, fold = pred_match.group(1), int(pred_match.group(2))
            info["prediction_folds"][split].append(fold)

        metrics_match = METRICS_RE.match(entry.name)
        if metrics_match:
            split, fold = metrics_match.group(1), int(metrics_match.group(2))
            info["metrics_folds"][split].append(fold)

    for split in ("train", "oos"):
        info["prediction_folds"][split] = sorted(set(info["prediction_folds"][split]))
        info["metrics_folds"][split] = sorted(set(info["metrics_folds"][split]))
        pred_folds = set(info["prediction_folds"][split])
        metric_folds = set(info["metrics_folds"][split])
        info["missing_metrics_for_predictions"][split] = sorted(pred_folds - metric_folds)

        if info["prediction_folds"][split]:
            first_fold = info["prediction_folds"][split][0]
            csv_path = run_dir / f"predictions_mr_{split}_{first_fold}.csv"
            info["csv_previews"][split] = read_csv_preview(csv_path, sample_rows)

        if info["metrics_folds"][split]:
            first_fold = info["metrics_folds"][split][0]
            metrics_path = run_dir / f"predictions_mr_{split}_{first_fold}_metrics.json"
            info["metrics_previews"][split] = read_metrics_preview(metrics_path)

    return info


def main() -> int:
    args = parse_args()
    data_root = Path(args.data_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "data_root": str(data_root),
        "data_root_exists": data_root.exists(),
        "runs": [inspect_run(data_root, run, args.sample_rows) for run in args.runs],
    }

    out_path = out_dir / "inspection_summary.json"
    with out_path.open("w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Wrote {out_path}")
    for run_info in summary["runs"]:
        print(
            "{run}: exists={exists} train_folds={train} oos_folds={oos} ls_dirs={ls}".format(
                run=run_info["run"],
                exists=run_info["exists"],
                train=len(run_info["prediction_folds"]["train"]),
                oos=len(run_info["prediction_folds"]["oos"]),
                ls=len(run_info["ls_dirs"]),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
