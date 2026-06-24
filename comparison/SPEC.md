# Comparison 2026-06-23 Specification

Version: 0.3  
Date: 2026-06-23  
Status: External-ready analysis specification

## 1. Purpose

This work sits inside a broader model-validation workflow for cross-sectional
signal research. The first question is not whether a strategy is profitable,
but whether the predictive ranking signal remains stable out-of-sample after
feature reduction.

This package compares the out-of-sample signal quality of three model output
folders:

```text
jo.base
jo.select
jo.select2
```

The main question is:

```text
Do the feature-selected runs differ materially from the baseline run out-of-sample?
```

The package is intentionally lightweight. It contains analysis code,
configuration, documentation, and small output artifacts. It does not contain
the heavy model output folders.

## 2. Scope

In scope:

- Inspect the three run folders: `jo.base`, `jo.select`, and `jo.select2`.
- Confirm available folds, prediction files, metrics files, columns, and LS folders.
- Compute train and OOS signal metrics for all available folds.
- Use Spearman rank IC as the primary comparison metric.
- Compare runs pairwise:
  - `select2 - base`
  - `select - base`
  - `select - select2`
- Produce CSV/JSON summaries and an executed notebook report.

Out of scope for this package:

- Full conditional PnL by quintile.
- Freshness or time-stop strategy implementation.
- Complete long/short backtest design.
- Costs, fees, slippage, and execution constraints.
- Solana / DeFi LP analytics.
- Training new models.
- Moving or copying the full raw data folders into the package.

## 3. Expected Inputs

The user must provide a `<DATA_ROOT>` directory containing:

```text
<DATA_ROOT>/
  jo.base/
  jo.select/
  jo.select2/
```

Expected prediction files:

```text
predictions_mr_oos_<fold>.csv
predictions_mr_train_<fold>.csv
```

Expected metrics files:

```text
predictions_mr_oos_<fold>_metrics.json
predictions_mr_train_<fold>_metrics.json
```

Expected prediction CSV columns:

```text
feature_index,date,coin,pred_6,pred_9,pred_blend,O_6,O_9,target_blend
```

Column meaning:

- `date`: cross-sectional date or timestamp used for per-date ranking evaluation.
- `coin`: asset identifier.
- `pred_6`: prediction for the 6-hour horizon.
- `pred_9`: prediction for the 9-hour horizon.
- `pred_blend`: blended prediction.
- `O_6`: realized target for the 6-hour horizon.
- `O_9`: realized target for the 9-hour horizon.
- `target_blend`: blended realized target.

## 4. Files

```text
README.md
SPEC.md
config.example.json
inspect_jo_runs.py
oos_compare.py
notebook_report.py
comparison_analysis.ipynb
outputs_jo_compare/
```

Purpose:

- `README.md`: user-facing execution guide.
- `SPEC.md`: technical and functional specification.
- `config.example.json`: example configuration.
- `inspect_jo_runs.py`: inspects folders, folds, columns, JSON metric keys, and LS directories.
- `oos_compare.py`: computes Spearman IC metrics and fold-level deltas.
- `notebook_report.py`: keeps notebook logic outside the notebook.
- `comparison_analysis.ipynb`: thin notebook containing only configuration and rendered outputs.
- `outputs_jo_compare/`: generated outputs. This folder can be included for review but should not be treated as source code.

## 5. Notebook Modes

- `auto`: use generated outputs if present; otherwise run inspection and comparison.
- `run`: run `inspect_jo_runs.py` and `oos_compare.py`, then render notebook outputs.
- `outputs`: render notebook outputs only from existing files in `outputs_jo_compare/`.

The recommended mode for an external reviewer who receives generated outputs is:

```python
"mode": "outputs"
```

The recommended mode for a reviewer who has access to the raw prediction
folders is:

```python
"mode": "run"
```

with `data_root` set to the local path containing `jo.base`, `jo.select`, and
`jo.select2`.

## 6. Metrics

Primary metric:

```text
Spearman(pred_blend, target_blend)
```

For each run, split, and fold:

1. Group rows by `date`.
2. Within each date, compute Spearman rank correlation between prediction and realized target.
3. Aggregate date-level IC values into fold-level statistics.

Secondary diagnostics:

```text
Spearman(pred_6, O_6)
Spearman(pred_9, O_9)
```

Existing Pearson metrics may be kept as reference, but they are not the primary
decision metric.

## 7. Comparisons

The comparison is paired by fold whenever possible:

```text
select2_minus_base
select_minus_base
select_minus_select2
```

The OOS split is the primary decision split. Train results are included to show
whether behavior transfers out-of-sample.

Decision guide:

- `base > select2 > select`: feature removal probably removed useful signal.
- `base ~ select2 > select`: `select2` is probably the reasonable compromise.
- `select2 ~ base`: moderate reduction is acceptable if stability is good.
- `select ~ select2 ~ base`: prefer the simpler model only after additional checks.
- `select` or `select2` better than `base`: feature reduction likely removed noise.

## 8. Outputs

Required outputs:

```text
inspection_summary.json
fold_metrics.csv
fold_deltas.csv
summary_by_run.csv
delta_summary.csv
```

Optional but useful outputs:

```text
date_ic.csv
decision_summary.md
compare_run_summary.json
comparison_analysis_executed.ipynb
```

Output meanings:

- `inspection_summary.json`: detected runs, folds, columns, missing files, metric keys, and LS directories.
- `fold_metrics.csv`: one row per run, split, fold, and metric.
- `fold_deltas.csv`: paired fold-level differences between runs.
- `summary_by_run.csv`: aggregate mean/median/stability summary by run and split.
- `delta_summary.csv`: aggregate delta summary for the three pairwise comparisons.
- `date_ic.csv`: date-level IC values for detailed diagnostics.
- `decision_summary.md`: concise text interpretation.
- `compare_run_summary.json`: execution metadata, output row counts, and warnings.
- `comparison_analysis_executed.ipynb`: executed notebook artifact containing rendered outputs.

## 9. Environment

The scripts are designed to run with the Python standard library. `pandas`,
`numpy`, and `scipy` are not required for the core computation.

Standard-library modules used include:

```text
argparse
csv
json
math
pathlib
statistics
collections
subprocess
```

To execute the notebook, a Jupyter environment is required.

## 10. Acceptance Criteria

The package is acceptable when:

- The notebook can be executed from existing outputs in `outputs` mode.
- The scripts can recompute outputs from raw prediction folders in `run` mode.
- OOS is clearly treated as the primary decision split.
- Spearman rank IC is computed per date and aggregated by fold.
- Pairwise fold-level deltas are produced.
- The final interpretation can answer whether feature selection preserved, improved, or degraded the OOS signal.

## 11. Follow-up Work

Recommended next steps after reviewing this package:

1. Confirm the OOS comparison conclusion.
2. Run conditional PnL by quintile to connect ranking quality to economic behavior.
3. Analyze signal freshness and time-stop rules if the signal remains usable.
4. Add costs, slippage, and risk constraints before any strategy-level conclusion.

The intended project sequence is therefore: signal validation first, economic
conditioning second, strategy mechanics third, and only then full backtest
interpretation. This package covers the first step and prepares the inputs for
the next two.
