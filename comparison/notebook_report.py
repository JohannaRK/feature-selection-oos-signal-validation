#!/usr/bin/env python3
"""Notebook-facing report utilities for the comparison analysis.

The notebook remains a thin configuration layer. This module contains mode
selection, optional processing calls, CSV parsing, and Markdown report creation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_OUTPUTS = [
    "inspection_summary.json",
    "fold_metrics.csv",
    "fold_deltas.csv",
    "summary_by_run.csv",
    "delta_summary.csv",
    "decision_summary.md",
    "compare_run_summary.json",
]
RUN_ORDER = ["base", "select", "select2"]
COLORS = {
    "base": "#246BFE",
    "select": "#1B9E77",
    "select2": "#D95F02",
    "select2_minus_base": "#D95F02",
    "select_minus_base": "#1B9E77",
    "select_minus_select2": "#6A3D9A",
    "h6": "#246BFE",
    "h9": "#D95F02",
}


def run_notebook(config: dict[str, Any]) -> str:
    """Run the configured workflow and render a Markdown report."""

    resolved = resolve_config(config)
    logs: list[str] = []
    mode = resolved["mode"]
    outputs_ready = required_outputs_available(resolved["out_dir"])

    if mode == "auto":
        mode = "outputs" if outputs_ready else "run"
        logs.append(f"Auto mode selected: {mode}")
    elif mode not in {"run", "outputs"}:
        raise ValueError('mode must be one of: "auto", "run", "outputs"')

    if mode == "outputs" and not outputs_ready:
        missing = missing_required_outputs(resolved["out_dir"])
        raise FileNotFoundError(
            "Output mode was requested, but required outputs are missing: "
            + ", ".join(missing)
        )

    if mode == "run":
        logs.extend(run_processing_scripts(resolved))

    report = build_markdown_report(resolved, logs)
    display_markdown(report)
    display_figures(resolved)
    print("Notebook report rendered.")
    return "notebook_report_rendered"


def resolve_config(config: dict[str, Any]) -> dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    out_dir = Path(config.get("out_dir", "outputs_jo_compare"))
    if not out_dir.is_absolute():
        out_dir = base_dir / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    return {
        "base_dir": base_dir,
        "mode": config.get("mode", "auto"),
        "data_root": Path(config.get("data_root", "data")),
        "out_dir": out_dir,
        "runs": list(config.get("runs", ["jo.base", "jo.select", "jo.select2"])),
        "splits": list(config.get("splits", ["train", "oos"])),
    }


def required_outputs_available(out_dir: Path) -> bool:
    return not missing_required_outputs(out_dir)


def missing_required_outputs(out_dir: Path) -> list[str]:
    return [name for name in REQUIRED_OUTPUTS if not (out_dir / name).exists()]


def run_processing_scripts(config: dict[str, Any]) -> list[str]:
    base_dir = config["base_dir"]
    out_dir = config["out_dir"]
    data_root = config["data_root"]
    runs = config["runs"]
    splits = config["splits"]

    commands = [
        [
            sys.executable,
            "-B",
            str(base_dir / "inspect_jo_runs.py"),
            "--data-root",
            str(data_root),
            "--out-dir",
            str(out_dir),
            "--runs",
            *runs,
        ],
        [
            sys.executable,
            "-B",
            str(base_dir / "oos_compare.py"),
            "--data-root",
            str(data_root),
            "--out-dir",
            str(out_dir),
            "--runs",
            *runs,
            "--splits",
            *splits,
        ],
    ]

    logs = []
    for command in commands:
        logs.append("$ " + " ".join(command))
        completed = subprocess.run(
            command,
            cwd=base_dir,
            check=True,
            text=True,
            capture_output=True,
        )
        if completed.stdout.strip():
            logs.append(completed.stdout.strip())
        if completed.stderr.strip():
            logs.append(completed.stderr.strip())
    return logs


def build_markdown_report(config: dict[str, Any], logs: list[str]) -> str:
    out_dir = config["out_dir"]
    summary_rows = read_csv_rows(out_dir / "summary_by_run.csv")
    delta_rows = read_csv_rows(out_dir / "delta_summary.csv")
    fold_rows = read_csv_rows(out_dir / "fold_metrics.csv")

    oos_blend = sort_run_rows(
        row for row in summary_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    )
    train_blend = sort_run_rows(
        row for row in summary_rows if row.get("split") == "train" and row.get("metric") == "blend"
    )
    oos_deltas = [
        row for row in delta_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    ]
    diagnostics = sort_run_rows(
        row for row in summary_rows if row.get("split") == "oos" and row.get("metric") in {"h6", "h9"}
    )
    fold_blend = [
        row for row in fold_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    ]

    sections = [
        "# Comparison 2026-06-23 Report",
        "",
        "Primary metric: OOS mean fold Spearman IC for `pred_blend` versus `target_blend`.",
        "",
        "## Executive Read",
        "",
        make_executive_read(oos_blend, oos_deltas),
        "",
        "## OOS Blend by Run",
        "",
        markdown_table(
            oos_blend,
            ["run_label", "n_folds", "mean_fold_ic", "median_fold_ic", "ci95_low", "ci95_high"],
        ),
        "",
        "## OOS Blend Deltas",
        "",
        markdown_table(
            sorted(oos_deltas, key=lambda row: row.get("delta_name", "")),
            ["delta_name", "n_folds", "mean_delta", "median_delta", "positive_folds", "negative_folds", "ci95_low", "ci95_high"],
        ),
        "",
        "## Train vs OOS Blend",
        "",
        markdown_table(build_train_oos_rows(train_blend, oos_blend), ["run", "train_mean_ic", "oos_mean_ic", "train_minus_oos"]),
        "",
        "## 6h / 9h OOS Diagnostics",
        "",
        markdown_table(diagnostics, ["run_label", "metric", "mean_fold_ic", "median_fold_ic", "ci95_low", "ci95_high"]),
        "",
        "## OOS Fold Snapshot",
        "",
        fold_snapshot(fold_blend),
        "",
        "## Figures",
        "",
        "The figures below show the same comparison visually: OOS blend IC by run, OOS pairwise deltas, fold-by-fold OOS behavior, and 6h/9h diagnostics.",
        "",
        "## Logs",
        "",
        code_block("\n\n".join(logs) if logs else "Existing outputs were used; no processing scripts were run in this notebook execution."),
    ]
    return "\n".join(sections)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: str | float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        parsed = as_float(value)
        return value if parsed is None else f"{parsed:.6f}"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def sort_run_rows(rows: Any) -> list[dict[str, str]]:
    order = {name: i for i, name in enumerate(RUN_ORDER)}
    return sorted(list(rows), key=lambda row: order.get(row.get("run_label", ""), 99))


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(fmt(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, divider, *body])


def make_executive_read(oos_rows: list[dict[str, str]], delta_rows: list[dict[str, str]]) -> str:
    if not oos_rows:
        return "No OOS blend summary is available."
    ordered = sorted(
        oos_rows,
        key=lambda row: as_float(row.get("mean_fold_ic")) or float("-inf"),
        reverse=True,
    )
    ranking = " > ".join(row.get("run_label", "?") for row in ordered)
    parts = [f"OOS blend ranking is **{ranking}**."]
    for name in ("select_minus_base", "select2_minus_base"):
        row = next((item for item in delta_rows if item.get("delta_name") == name), None)
        if row:
            parts.append(
                f"`{name}` mean delta is **{fmt(row.get('mean_delta'))}** "
                f"with CI [{fmt(row.get('ci95_low'))}, {fmt(row.get('ci95_high'))}]."
            )
    parts.append("This is a signal-quality comparison, not a full trading backtest.")
    return " ".join(parts)


def build_train_oos_rows(train_rows: list[dict[str, str]], oos_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_run: dict[str, dict[str, str]] = {}
    for row in train_rows:
        by_run.setdefault(row.get("run_label", ""), {})["train_mean_ic"] = row.get("mean_fold_ic", "")
    for row in oos_rows:
        by_run.setdefault(row.get("run_label", ""), {})["oos_mean_ic"] = row.get("mean_fold_ic", "")

    rows = []
    for run in RUN_ORDER:
        item = by_run.get(run, {})
        train = as_float(item.get("train_mean_ic"))
        oos = as_float(item.get("oos_mean_ic"))
        rows.append(
            {
                "run": run,
                "train_mean_ic": item.get("train_mean_ic", ""),
                "oos_mean_ic": item.get("oos_mean_ic", ""),
                "train_minus_oos": "" if train is None or oos is None else str(train - oos),
            }
        )
    return rows


def fold_snapshot(rows: list[dict[str, str]]) -> str:
    selected = []
    for row in rows:
        fold = as_float(row.get("fold"))
        value = as_float(row.get("mean_ic"))
        if fold is None or value is None:
            continue
        if int(fold) in {0, 1, 2, 24, 25, 26}:
            selected.append(row)
    if not selected:
        return "_No fold snapshot available._"
    selected = sorted(selected, key=lambda row: (int(float(row.get("fold", "0"))), row.get("run_label", "")))
    return markdown_table(selected, ["fold", "run_label", "mean_ic", "median_ic", "n_valid_dates"])


def code_block(text: str) -> str:
    return "```text\n" + text + "\n```"


def display_markdown(report: str) -> None:
    try:
        from IPython.display import Markdown, display  # type: ignore
    except Exception:
        print(report)
        return
    display(Markdown(report))


def display_figures(config: dict[str, Any]) -> None:
    out_dir = config["out_dir"]
    summary_rows = read_csv_rows(out_dir / "summary_by_run.csv")
    delta_rows = read_csv_rows(out_dir / "delta_summary.csv")
    fold_rows = read_csv_rows(out_dir / "fold_metrics.csv")

    oos_blend = sort_run_rows(
        row for row in summary_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    )
    oos_deltas = [
        row for row in delta_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    ]
    oos_fold_blend = [
        row for row in fold_rows if row.get("split") == "oos" and row.get("metric") == "blend"
    ]
    diagnostics = [
        row for row in summary_rows if row.get("split") == "oos" and row.get("metric") in {"h6", "h9"}
    ]

    figures = [
        bar_chart_svg(oos_blend, "run_label", "mean_fold_ic", "ci95_low", "ci95_high", "OOS blend mean Spearman IC"),
        bar_chart_svg(sorted(oos_deltas, key=lambda row: row.get("delta_name", "")), "delta_name", "mean_delta", "ci95_low", "ci95_high", "OOS blend pairwise deltas"),
        fold_line_svg(oos_fold_blend),
        grouped_metric_svg(diagnostics),
    ]
    render_svgs([figure for figure in figures if figure])


def render_svgs(figures: list[str]) -> None:
    if not figures:
        print("No figure data available.")
        return
    try:
        from IPython.display import SVG, display  # type: ignore
    except Exception:
        for figure in figures:
            print(figure)
        return
    for figure in figures:
        display(SVG(data=figure))


def escape_xml(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def bar_chart_svg(
    rows: list[dict[str, str]],
    label_col: str,
    value_col: str,
    low_col: str,
    high_col: str,
    title: str,
) -> str:
    values = [as_float(row.get(value_col)) for row in rows]
    lows = [as_float(row.get(low_col)) for row in rows]
    highs = [as_float(row.get(high_col)) for row in rows]
    numeric = [value for value in values + lows + highs if value is not None]
    if not numeric:
        return ""

    width, height = 840, 360
    left, right, top, bottom = 70, 30, 52, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_min = min(0.0, min(numeric))
    y_max = max(numeric)
    if y_min == y_max:
        y_max = y_min + 1.0
    pad = (y_max - y_min) * 0.16
    y_min -= pad
    y_max += pad

    def y_pos(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * plot_h

    zero_y = y_pos(0.0)
    band = plot_w / max(len(rows), 1)
    bar_w = min(90, band * 0.55)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-size="20" font-family="Arial" font-weight="700" fill="#111827">{escape_xml(title)}</text>',
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{width-right}" y2="{zero_y:.2f}" stroke="#9aa4b2" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#d1d5db" stroke-width="1"/>',
    ]
    for i, row in enumerate(rows):
        label = row.get(label_col, "")
        value = as_float(row.get(value_col))
        low = as_float(row.get(low_col))
        high = as_float(row.get(high_col))
        if value is None:
            continue
        x_center = left + band * i + band / 2
        y_value = y_pos(value)
        rect_y = min(y_value, zero_y)
        rect_h = max(abs(zero_y - y_value), 1)
        color = COLORS.get(label, "#4B5563")
        svg.append(
            f'<rect x="{x_center - bar_w / 2:.2f}" y="{rect_y:.2f}" width="{bar_w:.2f}" height="{rect_h:.2f}" fill="{color}"/>'
        )
        if low is not None and high is not None:
            y_low = y_pos(low)
            y_high = y_pos(high)
            svg.append(f'<line x1="{x_center:.2f}" y1="{y_high:.2f}" x2="{x_center:.2f}" y2="{y_low:.2f}" stroke="#111827" stroke-width="1.5"/>')
            svg.append(f'<line x1="{x_center - 8:.2f}" y1="{y_high:.2f}" x2="{x_center + 8:.2f}" y2="{y_high:.2f}" stroke="#111827" stroke-width="1.5"/>')
            svg.append(f'<line x1="{x_center - 8:.2f}" y1="{y_low:.2f}" x2="{x_center + 8:.2f}" y2="{y_low:.2f}" stroke="#111827" stroke-width="1.5"/>')
        svg.append(f'<text x="{x_center:.2f}" y="{height - 38}" text-anchor="middle" font-size="13" font-family="Arial" fill="#111827">{escape_xml(label)}</text>')
        svg.append(f'<text x="{x_center:.2f}" y="{rect_y - 8:.2f}" text-anchor="middle" font-size="12" font-family="Arial" fill="#374151">{escape_xml(fmt(value))}</text>')
    svg.append("</svg>")
    return "".join(svg)


def fold_line_svg(rows: list[dict[str, str]]) -> str:
    grouped: dict[str, list[tuple[int, float]]] = {}
    for row in rows:
        label = row.get("run_label", "")
        fold = as_float(row.get("fold"))
        value = as_float(row.get("mean_ic"))
        if label and fold is not None and value is not None:
            grouped.setdefault(label, []).append((int(fold), value))
    if not grouped:
        return ""

    width, height = 980, 380
    left, right, top, bottom = 64, 135, 52, 58
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_points = [point for points in grouped.values() for point in points]
    min_fold = min(fold for fold, _ in all_points)
    max_fold = max(fold for fold, _ in all_points)
    values = [value for _, value in all_points]
    y_min = min(0.0, min(values))
    y_max = max(values)
    if y_min == y_max:
        y_max = y_min + 1.0
    pad = (y_max - y_min) * 0.15
    y_min -= pad
    y_max += pad

    def x_pos(fold: int) -> float:
        if min_fold == max_fold:
            return left + plot_w / 2
        return left + (fold - min_fold) / (max_fold - min_fold) * plot_w

    def y_pos(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * plot_h

    zero_y = y_pos(0.0)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-size="20" font-family="Arial" font-weight="700" fill="#111827">OOS blend Spearman IC by fold</text>',
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{width-right}" y2="{zero_y:.2f}" stroke="#9aa4b2" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#d1d5db" stroke-width="1"/>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#d1d5db" stroke-width="1"/>',
        f'<text x="{left}" y="{height - 18}" font-size="12" font-family="Arial" fill="#5b6472">fold</text>',
    ]
    for label in RUN_ORDER:
        points = sorted(grouped.get(label, []))
        if not points:
            continue
        color = COLORS.get(label, "#4B5563")
        path = " ".join(
            ("M" if i == 0 else "L") + f" {x_pos(fold):.2f} {y_pos(value):.2f}"
            for i, (fold, value) in enumerate(points)
        )
        svg.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        for fold, value in points:
            svg.append(f'<circle cx="{x_pos(fold):.2f}" cy="{y_pos(value):.2f}" r="2.6" fill="{color}"/>')
    for i, label in enumerate(RUN_ORDER):
        color = COLORS.get(label, "#4B5563")
        y_legend = top + 8 + i * 24
        svg.append(f'<rect x="{width-right+20}" y="{y_legend-10}" width="13" height="13" fill="{color}"/>')
        svg.append(f'<text x="{width-right+40}" y="{y_legend+1}" font-size="13" font-family="Arial" fill="#111827">{escape_xml(label)}</text>')
    svg.append("</svg>")
    return "".join(svg)


def grouped_metric_svg(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    ordered = []
    for run in RUN_ORDER:
        for metric in ("h6", "h9"):
            match = next((row for row in rows if row.get("run_label") == run and row.get("metric") == metric), None)
            if match:
                ordered.append(match)
    return bar_chart_svg(
        [
            {
                **row,
                "label": f"{row.get('run_label', '')} {row.get('metric', '')}",
            }
            for row in ordered
        ],
        "label",
        "mean_fold_ic",
        "ci95_low",
        "ci95_high",
        "OOS 6h and 9h diagnostics",
    )


if __name__ == "__main__":
    run_notebook({"mode": "auto"})
