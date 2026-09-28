# Model card

Synoptiq is a meta-layer over external GFS, IFS, and AIFS forecasts. It does not replace those forecast systems. The intended production model set is nine LightGBM source-skill models: one per source and variable for precipitation, temperature, and wind, plus three calibrated bust-risk models.

Training must use real aligned forecast/verification pairs, chronological train/validation/test partitions, and an untouched test period. Reported metrics must come from the machine-readable real evaluation report. No target improvement is asserted by this repository until that report exists.

The common supported historical training period starts 2025-02-25. ECMWF is retrieved from the official Open Data AWS mirror using `ecmwf.opendata.Client(source="aws", beta=False)`; MARS is optional and is not required for the standard workflow. AIFS source provenance identifies Single v1 before 2026-05-12 and Single v2 from 2026-05-12 onward.

The production regime detector remains transparent and rule-based, using real meteorological context. Trust scoring, abstention, calibration, bias correction, dynamic weighting, and explanations are operational outputs only when the corresponding validated artifacts are available.
