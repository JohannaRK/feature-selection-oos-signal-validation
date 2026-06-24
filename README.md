# Comparison 2026-06-23

This folder contains a lightweight, reproducible analysis package for comparing
three model output folders:

```text
jo.base
jo.select
jo.select2
```

The objective is to compare out-of-sample signal quality and decide whether the
feature-selected runs preserve, improve, or degrade the baseline ranking signal.

The package does not contain the heavy input data. The user must provide the
path to the directory containing `jo.base`, `jo.select`, and `jo.select2`.

## Expected Input Layout

Set `<DATA_ROOT>` to a directory with this structure:

```text
<DATA_ROOT>/
  jo.base/
    predictions_mr_oos_0.csv
    predictions_mr_train_0.csv
    ...
  jo.select/
    predictions_mr_oos_0.csv
    predictions_mr_train_0.csv
    ...
  jo.select2/
    predictions_mr_oos_0.csv
    predictions_mr_train_0.csv
    ...
```

Expected prediction CSV columns:

```text
feature_index,date,coin,pred_6,pred_9,pred_blend,O_6,O_9,target_blend
```

## Two Execution Modes

The notebook supports two practical modes:

- `run`: compute outputs from the raw prediction folders, then render the report.
- `outputs`: render the report from already generated files in `outputs_jo_compare/`.
- `auto`: use existing outputs if present; otherwise run the full computation.

The notebook is deliberately tiny:

```text
comparison_analysis.ipynb
```

It acts like a configuration file. The implementation lives in:

```text
notebook_report.py
inspect_jo_runs.py
oos_compare.py
```

## Run From Raw Prediction Folders

From this directory:

```bash
python3 -B inspect_jo_runs.py \
  --data-root <DATA_ROOT> \
  --out-dir outputs_jo_compare

python3 -B oos_compare.py \
  --data-root <DATA_ROOT> \
  --out-dir outputs_jo_compare
```

Then execute `comparison_analysis.ipynb` with:

```python
CONFIG = {
    "mode": "outputs",
    "data_root": "data",
    "out_dir": "outputs_jo_compare",
    "runs": ["jo.base", "jo.select", "jo.select2"],
    "splits": ["train", "oos"],
}
```

## Render From Existing Outputs

If `outputs_jo_compare/` is already present, no raw data is needed. Open
`comparison_analysis.ipynb`, keep:

```python
"mode": "outputs"
```

and run the two code cells.

The executed notebook artifact can be produced with:

```bash
jupyter nbconvert --to notebook --execute comparison_analysis.ipynb \
  --output-dir outputs_jo_compare \
  --output comparison_analysis_executed.ipynb \
  --ExecutePreprocessor.timeout=600
```

## Generated Outputs

The analysis produces:

```text
outputs_jo_compare/inspection_summary.json
outputs_jo_compare/fold_metrics.csv
outputs_jo_compare/fold_deltas.csv
outputs_jo_compare/summary_by_run.csv
outputs_jo_compare/delta_summary.csv
outputs_jo_compare/date_ic.csv
outputs_jo_compare/decision_summary.md
outputs_jo_compare/compare_run_summary.json
outputs_jo_compare/comparison_analysis_executed.ipynb
```

## Scope

This package covers the first comparison step only: train/OOS signal metrics.
Conditional PnL, freshness, time-stop, transaction costs, and full strategy
backtesting are follow-up analyses.
