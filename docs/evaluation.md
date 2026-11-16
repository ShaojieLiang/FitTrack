# FitTrack reproducible evaluation

**SYNTHETIC DATA ONLY. These results demonstrate the implementation, not real-world fitness efficacy.**

- Source: invented fixture; fixed seed 2027; no personal records.
- Target: next same-exercise, same-equipment, same-weight first work-set repetitions.
- Comparable sessions: 120; chronological test predictions: 90.
- Test range: 2025-01-31 to 2025-04-29.
- Method: expanding-window one-step evaluation; minimum 12 labeled training samples per group.
- Fixed Ridge alpha=10. Median imputation and scaling are fitted only on each training window.
- Initial fixture: 120 calendar days, 60 training days, 109 body-measurement days; 11 days without body measurements. Non-training days are not assumed to be failed/missing workouts.
- Body inputs use measurements strictly before each target day; missing body readings remain missing until train-only imputation.
- Synthetic equipment and set labels are known. Real API data may lack these; unknown labels/equipment are excluded from forecasting.

| Method | MAE (reps; lower is better) |
| --- | ---: |
| last | 1.0889 |
| mean3 | 0.9630 |
| ridge_training | 1.0912 |
| ridge_body | 1.1142 |

## Feedback replay

A forecast is saved before the target day's synthetic record is imported. This is an offline chronological replay, not a real live user trial.

- Forecast created: 2025-04-30T20:00:00+08:00; data cutoff: 2025-04-29.
- Target day: 2025-05-01; predicted: 9.0; actual: 9.0 reps.
- Absolute error: 0.00 reps.
- Advice saved with the forecast: 维持当前重量与目标次数；记录实际完成次数和主观强度，再判断是否调整。
- Next target: 2025-05-03; next prediction: 9.0 reps.
- Method selected from prior-only validation: `last_validation_fallback`. Ridge is used only with at least five validation errors and lower MAE than the last-session baseline.
- Advice adoption is unknown unless supplied explicitly; no adherence is inferred.

## Interpretation and limitations

Compare all methods, including the training-only ablation; adding body data may fail to improve error. No claim of model superiority is made outside these synthetic records. Repetitions depend on effort, rest, technique and prescribed targets; a date and equipment match cannot fully control these. Sparse real data produces an explicit insufficient-data status. No muscle gain, fat loss, injury risk or causal benefit is predicted or established. Advice is a transparent rule layer, not an optimized or clinically validated prescription.

## Real-data validation

Not performed in this public project. A later private evaluation must report its dates, comparable sample counts, missingness and chronological errors separately. A prospective training-effect study would be needed to support claims that the advice improves outcomes.
