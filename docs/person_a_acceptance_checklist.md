# Person A acceptance checklist

Use this checklist before declaring the data/ML workstream complete.

## Synthetic data
- [ ] Every generated table is clearly marked synthetic and includes seed/version metadata.
- [ ] Same-seed reruns reproduce all substantive values (ignore the generation timestamp).
- [ ] Resident, hostel, menu, meal, attendance and operations identifiers reconcile.
- [ ] Attendance interval arrivals reconcile to cumulative attendance for every meal.
- [ ] Quantity rules hold: 0 <= consumed <= served <= prepared.
- [ ] Untouched leftovers = prepared - served; plate waste = served - consumed.
- [ ] Empty event data is valid; other required datasets are non-empty.
- [ ] Starter menu entries are verified against the source menu images before presentation.

## Features and forecasting
- [ ] Every feature is available at the exact time the forecast is made.
- [ ] Lag and rolling features use only prior observations for the same dish and meal.
- [ ] Evaluation uses chronological holdout dates, with no target leakage into training or baseline.
- [ ] Baseline and context model use identical holdout rows and metrics.
- [ ] MAE/RMSE, train/test ranges, seed and model version are saved in a machine-readable report.
- [ ] Any prediction intervals are calibrated on held-out residuals before being called confidence intervals.
- [ ] Synthetic evaluation results are explicitly not presented as real-world waste reduction.

## Handover
- [ ] Clean checkout installs from requirements.txt.
- [ ] Generator, validator, tests, evaluation and prediction commands run successfully.
- [ ] Person B can call the documented forecast interface and receives the agreed output schema.
- [ ] Commit SHA, dataset seed/version, model version and evaluation report are recorded.

## Completion rule
Do not mark Person A complete solely because scripts exist. Check every item above and attach
command output or saved artifacts as evidence.
