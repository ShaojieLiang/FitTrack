# Architecture and data contract

FitTrack is a local Python CLI backed by SQLite. Public artifacts are generated from invented fixtures. It does not require a server, account or API access for its demo.

```text
User-configured server   Normalized JSON       Invented fixture
         \                    |                    /
          ---- validate and normalize units -------
                              |
                    atomic SQLite upserts
                              |
            historical queries and comparable groups
                              |
          past-only features + walk-forward evaluation
                              |
             immutable forecast + rule-based advice
                              |
             explicit observed outcome + next forecast
```

## Tables

| Table | Grain and key | Purpose |
| --- | --- | --- |
| sessions | source + external session ID | Training dates and session titles |
| sets | source + session + movement position + set position | Exercise, equipment, group type, completion, kg, reps, RPE and actual duration in seconds |
| body | source + local date + metric | Daily measurement value, unit and optional measurement timestamp |
| forecasts | hash of source + exercise + equipment + kg + target date | Immutable prediction snapshot, model, cutoff, suggestion and later explicit feedback |

Repeated imports update existing sessions atomically and rebuild their sets; they do not duplicate completed volume. This is an upsert cache, not a remote deletion mirror. A failed batch changes nothing. Different sources remain separate during modeling. One body metric per source/date is supported; conflicting intraday measurements must be resolved before import. No missing measurement is interpreted as zero.

The normalized input is illustrated in [minimal-synthetic.json](../examples/minimal-synthetic.json). Weight units must be explicit kg or lb; lb is converted to kg. Body units are metric-specific. Timestamps require an offset and the same local date as their measurement. No timestamp is inferred from import time. Supported optional manual metrics include weight, body fat, waist, muscle mass, blood pressure and pulse; no medical inference is performed.

## Comparable sessions and features

For each movement take its first explicitly labeled work set, requiring completion, known equipment, weight and reps. Do not substitute a later completed set if the first work set is unfinished. Unknown set types, warmups and cardio are excluded. Multiple sessions on the same date within a comparison group are excluded because order is unknown. Group identity is source + exact exercise + equipment + weight rounded to five kg decimals.

The seven model features are last reps, last-three mean, last-three change, days since last comparable session, previous-seven-day comparable-session count, previous-seven-day median body weight and previous-seven-day median body fat. All readings are strictly before the target local date. No cross-exercise tonnage is used to claim progress. Days without body data stay missing. Median imputation (with missing indicators), scaling and Ridge regression fit only on each chronological training window.

Three prior comparable sessions are needed to form a labeled sample; twelve labeled samples are required to fit a model. These are software minimums, not guarantees of reliable performance. More real validation observations may be necessary. Unobserved effort, technique, prescribed targets and rest limit interpretation.

## Prediction and feedback lifecycle

Evaluation uses expanding windows, training on earlier samples and predicting the next sample. Fixed alpha=10 avoids selecting parameters on the reported test samples. Compare last-session, three-session mean, training-only Ridge and Ridge with body features. The body-feature ablation tests whether body information helps on the evaluated dataset.

Live forecasting uses Ridge only when at least five past-only validation predictions exist and its MAE is lower than last-session persistence; otherwise it uses the last-session baseline. This gate is a policy, not an independently validated model selector. Public evaluation reports each underlying method separately.

The CLI permits forecast targets only after the current Shanghai calendar day. An immutable forecast is saved before feedback is accepted. Feedback records actual reps, date and optional advice adoption. A user must confirm that supplied feedback refers to the comparable movement and load; FitTrack cannot infer this from a reps value alone. The next forecast uses newly imported training history. Merely entering feedback does not fabricate a training session or retrain a model.

The demo replays historical synthetic dates, saves a forecast, imports a later synthetic session, attaches the observed outcome and generates another forecast. This replay demonstrates sequencing; it is not a live prospective study.

## Scope

Implemented: storage, import, query, static figures, simple forecasting, chronological evaluation, advice rules and feedback persistence. Optional server endpoints and credentials are blank until supplied by the user. The normalized server contract is covered by mocks; live private server access has not been tested. Standalone image OCR, conversational coaching, mobile UI, injury prediction, body-composition forecasting and automatic plan writes are outside this version.

Method references: [scikit-learn chronological evaluation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split), [Ridge regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html).
