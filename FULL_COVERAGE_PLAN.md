# Full Coverage Plan

This document checks whether the current `Comparison` package covers the full
scope of the source material: the dated mail/discussion notes, `XS_MR_REFINEMENTS.md`,
and `utils_trade_viz.py`.

It is a planning document only. It does not implement new analysis code, does
not change the current comparison scripts, and does not start a backtest.

## 1. Verdict

The current `Comparison` package fully covers the narrow 23/06 task:

- compare `jo.base`, `jo.select`, and `jo.select2`;
- focus first on out-of-sample signal quality;
- use cross-sectional Spearman rank IC as the main OOS ranking metric;
- generate lightweight outputs and an executed notebook;
- keep the heavy remote prediction folders out of the local repository.

It does not fully cover the whole project scope implied by:

- `../Doc_mails_recu_envoi`;
- `../XS_MR_REFINEMENTS.md`;
- `../utils_trade_viz.py`.

Those sources are partially covered and, in some places, extended by the current
work. The current package is therefore a first validated block, not the complete
project plan.

## 2. Coverage Summary

| Source area | Current coverage | Explanation |
| --- | --- | --- |
| 23/06 OOS comparison of `jo.base`, `jo.select`, `jo.select2` | Covered | This is the exact scope of the current `Comparison` scripts, outputs, and notebook. |
| A1: signal quality / ranking / conditional PnL by quantile | Partially covered | OOS rank IC is covered. Conditional PnL by quintile is only listed as a follow-up. |
| A2: long/short exploitation, allocation, exits, risk | Partially covered | Mentioned as the next layer after signal validation. Not implemented or validated yet. |
| Piste 3: Solana / DeFi | Intentionally not covered | Treated as a separate exploratory data track, not part of the current comparison. |
| `XS_MR_REFINEMENTS.md` | Partially covered | Freshness and time-stop are identified as next steps, but the eight refinements are not fully executed or tested. |
| `utils_trade_viz.py` | Partially covered | It is recognized as the tool for PnL/freshness/time-stop diagnostics, but the current package does not yet validate or run its full workflow. |
| Regime work | Partially covered | Regime is mentioned as an important future feature/risk branch, but not included in the current OOS comparison. |
| Feature-selection branch beyond the three existing runs | Partially covered | The existing comparison gives a first answer. It does not yet cover `jo.cluster2`, with/without regime, or new reruns. |
| Volume anomaly / volatility clustering notes | Not covered | These belong to separate research branches mentioned in the dated notes. |
| Full backtest with costs/slippage | Not covered | Explicitly out of scope until signal, conditional PnL, freshness, and exits are validated. |

## 3. Operating Principles

The next work should remain staged and falsifiable:

1. Do not move directly from OOS rank IC to a full trading backtest.
2. First validate whether the signal ranking has economic meaning.
3. Then validate whether signal freshness and position lifetime improve the
   conditional PnL.
4. Only after that, test allocation, exits, risk, costs, and slippage.
5. Keep notebooks thin: configuration and outputs only. The logic should live in
   external Python modules.
6. Keep generated heavy data out of Git. Only commit scripts, specs, notebooks,
   and lightweight summaries.

## 4. Complete Step-by-Step Plan

### Phase 0 - Close the Current Comparison Block

Goal: finish the narrow `Comparison` package cleanly before expanding scope.

Substeps:

1. Keep the current OOS conclusion visible:
   - `base` has the strongest OOS blend IC;
   - `select` is slightly below `base`;
   - `select2` is clearly below `base` on the current OOS blend metric.
2. Confirm that the generated outputs are present:
   - `outputs_jo_compare/inspection_summary.json`;
   - `outputs_jo_compare/summary_by_run.csv`;
   - `outputs_jo_compare/fold_metrics.csv`;
   - `outputs_jo_compare/fold_deltas.csv`;
   - `outputs_jo_compare/delta_summary.csv`;
   - `outputs_jo_compare/date_ic.csv`;
   - `outputs_jo_compare/decision_summary.md`.
3. Keep the notebook as a report layer, not as the source of analysis logic.
4. Do not interpret the OOS IC comparison as a full trading result.

Decision produced by this phase:

- The feature-selection runs do not currently beat the base run on the primary
  OOS blend rank metric.

### Phase 1 - Bridge OOS Signal Metrics to Conditional PnL Data

Goal: move from "does the model rank well?" to "does the ranking create useful
conditional PnL structure?"

Substeps:

1. Identify which existing remote outputs can produce or already contain:
   - trade-level entry dates;
   - side;
   - coin;
   - signal rank or quantile at entry;
   - PnL path by age;
   - final PnL;
   - exit type;
   - time spent in quartile;
   - time to median crossing.
2. Map those fields to the schemas expected by `utils_trade_viz.py`:
   - `pnl_panel_<fold>.csv`;
   - `quartile_<fold>.csv`.
3. Check whether the current `jo.base`, `jo.select`, and `jo.select2` outputs
   are enough to build these files, or whether a new extraction script is needed.
4. Keep this phase read-only until the required fields are confirmed.

Expected result:

- A clear data bridge plan from prediction/ranking outputs to the PnL diagnostic
  datasets required by `utils_trade_viz.py`.

### Phase 2 - Validate `utils_trade_viz.py` Before Using It on Real Data

Goal: ensure the diagnostic tool is trustworthy before drawing conclusions from
its figures.

Substeps:

1. Audit the expected input schemas:
   - `pnl_panel`: `coin`, `side`, `entry_date`, `age`, `T`, `pnl_t`,
     `final_pnl`, `exit_type`;
   - `quartile_dataset`: `coin`, `side`, `entry_date`, `age`,
     `time_in_quartile`, `time_to_median_crossing`, `median_crossed`.
2. Use the existing synthetic-data test source if appropriate.
3. Generate controlled synthetic cases:
   - positive case where long top / short bottom should work;
   - null case where no quantile structure should appear;
   - adversarial or permuted case where the signal should fail.
4. Run the main diagnostic functions on those cases:
   - PnL path panel;
   - quartile persistence panel;
   - exit quality;
   - reversal diagnostics;
   - lifetime versus PnL;
   - freshness effect.
5. Verify that expected effects are visible only in the positive synthetic case.
6. Fix or document unit/time conventions before using the figures:
   - the `bars_per_day` labeling must be checked carefully, because `48`
     bars/day corresponds to 30-minute bars, not 3-minute bars.

Decision produced by this phase:

- Either `utils_trade_viz.py` is reliable enough for real diagnostics, or it
  needs targeted fixes before it can be used.

### Phase 3 - A1: Conditional PnL by Signal Quantile

Goal: answer the original A1 question more directly than OOS IC alone.

Substeps:

1. Build or locate the real `pnl_panel` and `quartile_dataset` files.
2. Compute PnL conditional on signal bucket or quintile.
3. Compare top-ranked and bottom-ranked assets in the intended long/short
   direction.
4. Measure whether extreme ranks behave differently from middle ranks.
5. Test whether stale extreme ranks lose predictive value.
6. Use bootstrap or fold-level aggregation to avoid over-interpreting one fold.
7. Compare against a permuted or null baseline if possible.

Expected outputs:

- fold-level conditional PnL tables;
- quintile or bucket plots;
- top-minus-bottom spread diagnostics;
- a short decision summary.

Decision produced by this phase:

- The ranking signal either has usable economic structure, has weak structure,
  or does not justify moving to strategy mechanics.

### Phase 4 - A2 First Layer: Freshness and Time-Stop

Goal: test the simplest strategy-relevant refinements before allocation and
full backtesting.

Primary source links:

- `XS_MR_REFINEMENTS.md` item #3: Freshness Filter;
- `XS_MR_REFINEMENTS.md` item #7: Time-Stop;
- the dated discussion notes about ranking freshness and maximum position age.

Substeps for freshness:

1. Define stale positions as assets that remain in extreme ranks for too long.
2. Compute time-in-quartile or equivalent rank-age variables.
3. Split positions by freshness bucket.
4. Compare conditional PnL for fresh versus stale signals.
5. Check whether stale extreme ranks become less profitable or reverse.

Substeps for time-stop:

1. Estimate PnL path by position age.
2. Estimate when winners usually reach peak or flatten.
3. Estimate when losers deteriorate.
4. Test candidate maximum holding times.
5. Compare candidate time-stops against no time-stop.

Decision produced by this phase:

- Promote freshness/time-stop only if they improve conditional PnL or reduce
  bad tails without destroying the core signal.

### Phase 5 - Remaining `XS_MR_REFINEMENTS.md` Ideas

Goal: cover the rest of the refinement document in the right order, without
mixing all ideas at once.

Recommended order from the refinement document:

1. Regime Gate.
2. Time-Stop.
3. Freshness Filter.
4. Approach Speed.
5. Asymmetric Slot Allocation.
6. Quality-Conditional Exit Quantiles.
7. Trapped-Flow.
8. MAE-Based Hard Stop.

Detailed substeps by refinement:

#### #1 Regime Gate

1. Define regime variables causally.
2. Test whether the signal behaves differently across regimes.
3. Avoid using a complex regime model before simple causal indicators are
   validated.
4. Decide whether regime is used as:
   - a feature;
   - a filter;
   - a risk overlay;
   - a future model-splitting rule.

#### #2 Asymmetric Slot Allocation

1. Use only after signal and regime behavior are understood.
2. Test whether long and short sides deserve different numbers of slots.
3. Compare symmetric versus asymmetric allocation under the same signal.
4. Do not validate this before A1 and the first A2 diagnostics.

#### #3 Freshness Filter

Covered in Phase 4.

#### #4 Approach Speed

1. Measure how quickly an asset moves toward an extreme rank.
2. Test whether fast movers behave differently from slow movers.
3. Combine speed with rank only after the rank-only baseline is clear.
4. Check whether speed adds information or only duplicates rank intensity.

#### #5 Trapped-Flow

1. Use only if the required market microstructure or derivatives data exists.
2. Confirm availability of fields such as funding, open interest, liquidation
   proxies, or equivalent pressure indicators.
3. Do not force this refinement if the data source is missing.

#### #6 Quality-Conditional Exit Quantiles

1. Define signal quality using validated features such as freshness, speed, or
   regime.
2. Estimate different exit thresholds by quality group.
3. Compare against a single common exit rule.
4. Promote only if the conditional exit improves outcomes out of sample.

#### #7 Time-Stop

Covered in Phase 4.

#### #8 MAE-Based Hard Stop

1. Confirm that maximum adverse excursion can be measured properly.
2. Estimate bad-tail behavior by side, rank bucket, and age.
3. Test hard stops after the time-stop analysis, not before.
4. Include this only if it reduces tail losses without damaging expected value.

### Phase 6 - Full Strategy / Backtest Layer

Goal: move from validated diagnostics to a tradable strategy only if the previous
phases justify it.

Substeps:

1. Write a separate strategy/backtest spec before implementation.
2. Define:
   - entry rules;
   - exit rules;
   - position sizing;
   - long/short slot counts;
   - maximum age;
   - rebalance frequency;
   - costs;
   - slippage;
   - liquidity constraints;
   - risk limits.
3. Use the validated A1/A2 diagnostics as constraints, not as decoration.
4. Run a simple baseline strategy before adding refinements.
5. Add refinements one by one.
6. Keep fold/OOS separation strict.

Decision produced by this phase:

- Only then decide whether there is a strategy worth presenting as a backtest.

### Phase 7 - Feature-Selection and Cluster Branch

Goal: avoid over-concluding from the current three-run comparison.

Substeps:

1. Treat the current `Comparison` result as a first OOS signal-quality answer.
2. Do not say feature selection is globally useless; say these two selection
   variants did not beat the base run on the current OOS blend IC.
3. Confirm whether a `jo.cluster2` run exists.
4. If available, compare cluster-based selection with the same OOS protocol.
5. If regime features exist, compare with and without them explicitly.
6. If a new run is needed, document its hypothesis before launching it.

Decision produced by this phase:

- Decide whether to keep the base feature set, retry a less aggressive selection,
  test clustering, or postpone feature selection until the economic diagnostics
  are clearer.

### Phase 8 - Regime Branch

Goal: keep the regime work separate enough to remain clean, but connected enough
to feed the signal/strategy analysis later.

Substeps:

1. Follow the regime V0 principle: simple, causal, reviewable indicators first.
2. Use indicators such as BTC trend, BTC volatility, and cross-sectional
   correlation before complex models.
3. Validate whether regimes explain signal behavior.
4. Only later decide whether regime should become:
   - a feature;
   - a filter;
   - a risk control;
   - a separate model segmentation rule.

Decision produced by this phase:

- Regime becomes part of the strategy only if it adds measurable explanatory or
  predictive value.

### Phase 9 - Separate Solana / DeFi Track

Goal: keep the Solana/DeFi idea from contaminating the A1/A2 validation path.

Substeps:

1. Treat Solana/DeFi as a separate exploratory data project.
2. First verify whether historical data exists for:
   - DeFi volume;
   - fees;
   - protocol-level activity;
   - relevant Solana ecosystem metrics.
3. Only after data availability is confirmed, write a separate plan.
4. Do not mix this with the `Comparison` package or the A1/A2 diagnostics unless
   the project direction explicitly changes.

## 5. Source-to-Plan Mapping

| Source | What it asks or implies | Where it is covered in this plan |
| --- | --- | --- |
| `Doc_mails_recu_envoi/20052026/pistes.txt` | A1 conditional PnL, A2 allocation, Solana/DeFi as separate piste | Phases 3, 4, 6, and 9 |
| `Doc_mails_recu_envoi/21052026/choix_des_pistes_travail.txt` | Focus on volets 1 and 2, freshness, position lifetime, thin notebook with Python modules | Phases 1, 2, 3, 4, and 6 |
| `Doc_mails_recu_envoi/21052026/claudes.txt` | Raw refinement ideas later summarized in `XS_MR_REFINEMENTS.md` | Phases 4 and 5 |
| `Doc_mails_recu_envoi/23062026/generated_explanations*` | 23/06 framing: A1 before A2, OOS signal first, avoid over-linking unrelated pistes | Phases 0, 3, 4, and 9 |
| `Doc_mails_recu_envoi/23062026/new_conv*` | Existing OOS prediction outputs, blend targets, feature-selection runs | Phases 0 and 7 |
| `XS_MR_REFINEMENTS.md` | Eight concrete refinements for XS mean-reversion strategy improvement | Phases 4, 5, and 6 |
| `utils_trade_viz.py` | Diagnostic functions for PnL paths, quartile persistence, exit quality, reversal, lifetime, freshness | Phases 2, 3, and 4 |
| Regime specification notes | Build simple causal regime indicators before advanced modeling | Phase 8 |

## 6. What Is Not Yet Covered by Existing Implementation

The current implemented `Comparison` package does not yet:

- build `pnl_panel_<fold>.csv`;
- build `quartile_<fold>.csv`;
- run the `utils_trade_viz.py` diagnostics on real data;
- validate freshness or time-stop rules;
- test the eight `XS_MR_REFINEMENTS.md` ideas;
- run a cost-aware backtest;
- test slippage or liquidity constraints;
- validate Solana/DeFi data availability;
- implement a regime gate;
- compare `jo.cluster2` if such a run exists.

## 7. Folder Recommendation

For now, it is acceptable to keep this planning document inside `jo_compare`
because it explains how the current comparison relates to the broader project.

However, if the next work expands beyond the OOS comparison, a new sibling
folder should be created at the repository level. Recommended names:

- `signal_strategy_validation`;
- `xs_mr_validation`;
- `volet1_volet2_validation`;
- `strategy_refinements`.

Do not create a new `git clone` inside `jo_compare`. That would nest one
repository inside another and make Git tracking confusing unless a submodule is
explicitly intended.

Better options:

1. Create a normal sibling folder inside the same repository for the next plan,
   scripts, and notebooks.
2. If a fully separate repository is required, clone it outside the current
   repository.
3. If a nested repository is truly required, use a Git submodule deliberately,
   with a clear reason and documented commands.

Recommended practical choice:

- keep `jo_compare` for the completed OOS comparison package;
- create a sibling folder later for the broader A1/A2 and XS-MR validation work.

