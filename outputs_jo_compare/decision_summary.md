# Comparison Decision Summary

Primary decision metric: OOS mean fold Spearman IC for `pred_blend` vs `target_blend`.

This is a signal-quality comparison, not a full trading backtest.

## OOS Blend by Run

| run | n_folds | mean_fold_ic | median_fold_ic | ci95_low | ci95_high |
| --- | ---: | ---: | ---: | ---: | ---: |
| base | 27 | 0.0377531508435 | 0.0459423252216 | 0.0218688548151 | 0.0536374468718 |
| select | 27 | 0.033225740302 | 0.0411638907879 | 0.0194914558524 | 0.0469600247516 |
| select2 | 27 | 0.0266554742523 | 0.0339886334132 | 0.0128093013388 | 0.0405016471659 |

## OOS Blend Deltas

| delta | n_folds | mean_delta | median_delta | positive | negative | ci95_low | ci95_high |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| select2_minus_base | 27 | -0.0110976765911 | -0.0107709752201 | 8 | 19 | -0.0212908149778 | -0.00090453820442 |
| select_minus_base | 27 | -0.0045274105415 | -0.00407063449162 | 12 | 15 | -0.0143738403706 | 0.00531901928758 |
| select_minus_select2 | 27 | 0.00657026604961 | 0.00141829008507 | 14 | 13 | -0.00399273264137 | 0.0171332647406 |

## Interpretation Guide

- `base > select2 > select`: feature removal probably removed useful signal.
- `base ~ select2 > select`: `select2` is the likely compromise; `select` is too aggressive.
- `select2 ~ base`: moderate reduction is acceptable if stability is good.
- `select/select2 > base`: feature reduction likely removed noise.

Follow-up work should only move to conditional PnL, freshness, and time-stop after this OOS comparison is reviewed.
