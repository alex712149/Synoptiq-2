# Synoptiq Live Data Integrity Report

## Runtime evidence

- Runtime mode: `real`
- Active model version: `synoptiq-real-12m-20260929`
- Synthetic data: `false`
- Live state after fresh refresh: `REAL LIVE`
- Fresh cycle time: 2026-09-29T18:17:00+00:00
- AIFS source run: 2026-09-29T00:00:00+00:00
- AIFS generation: AIFS Single v2

## Root cause fixed

Official ECMWF GRIB metadata identified precipitation as:

- field: `tp` / Total Precipitation
- native unit: `kg m**-2`
- step type: `accum`
- semantics: cumulative total precipitation since forecast start

The previous live normalization treated the legacy field name `tp_cum_m` as metres and multiplied cumulative differences by 1000. That produced values such as approximately 6597.7 mm/24h and allowed calibration to conceal the invalid raw input.

The corrected conversion is:

```text
24h precipitation = cumulative_tp(t + 24h) - cumulative_tp(t)
1 kg m^-2 = 1 mm
```

No cumulative values are summed together, and calibration is applied only after semantic source validation.

## Provider audit

| Provider | Native field | Native unit | Conversion | Aggregation | Lead mapping | Current status | Reason |
|---|---|---|---|---|---|---|---|
| GFS | APCP 6-hour accumulation | kg m^-2 / mm | 1 kg m^-2 = 1 mm | representative-point mean; 24h sum of four incremental 6h buckets | 24/48/72/96/120h | VALID / LIVE | finite, complete, future, semantic gate passed |
| IFS | `tp` cumulative total precipitation | kg m^-2 | cumulative difference over 24h; no x1000 | representative-point mean | 24/48/72/96/120h | VALID / LIVE | ECMWF metadata verified: `stepType=accum`, `tp` is cumulative |
| AIFS | `tp` cumulative total precipitation | kg m^-2 | cumulative difference over 24h; no x1000 | representative-point mean | 24/48/72/96/120h | VALID / LIVE | official ECMWF Open Data, AIFS Single v2, semantic gate passed |

Each live cycle contains 45 rows: 3 regions x 3 variables x 5 leads, with finite values and no duplicate region/variable/lead/valid-time records.

## Fresh +72h precipitation cases

| Region | GFS | IFS | AIFS | GFS weight | IFS weight | AIFS weight | Raw blend | Calibrated | Final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| KWG | 5.97 | 3.27 | 6.60 | 0.3707 | 0.3421 | 0.2872 | 5.23 | 4.15 | 4.15 |
| BOB | 0.27 | 0.00 | 0.34 | 0.3366 | 0.3381 | 0.3253 | 0.20 | 0.26 | 0.26 |
| IGP | 0.37 | 0.50 | 0.16 | 0.3226 | 0.3350 | 0.3424 | 0.34 | 0.26 | 0.26 |

The values above are runtime API outputs from `/api/v1/forecast/blend`, not fixture values.

## Quality gate

A provider is eligible for LIVE status and blending only when all of the following pass:

- model identity
- finite values
- complete regions, variables, and leads
- no duplicates
- future valid timestamps
- precipitation native unit and accumulation semantics
- physical semantic ranges: precipitation 0..1000 mm/24h, temperature -90..65 deg_C, wind 0..150 km/h

Invalid semantic data is returned as `INVALID` and excluded from persisted provider rows/blend readiness. It is never relabeled as LIVE and never rescued by calibration.

## Repository scan classification

- The old `6597.7` anomaly appears only in this report's root-cause explanation and the intentional `test_multi_thousand_precipitation_is_rejected_before_blend` test fixture. It is not present in the corrected live provider output.
- The synthetic generator and frontend mock/fixture objects remain in their explicit DEMO-only paths. REAL mode selects the FastAPI live API and validated REAL_12M artifacts; the API gateway rejects fixture responses in REAL mode.
- `0.000` score values in REAL_12M precipitation CSI artifacts are measured zero categorical scores, not missing values. The UI preserves that distinction and does not promote them as headline wins.
- No live path uses `fallback_value`, `fallback_forecast`, dummy AIFS data, or a hardcoded live forecast object.

## Calibration and guidance

- Extreme precipitation probability is shown only when the matching real isotonic event artifact exists.
- Temperature and wind use deterministic threshold guidance when event calibration is unavailable.
- Calibration is post-processing and cannot repair invalid units, accumulation, lead mapping, or aggregation.

## Verification and confidence

- REAL_12M verification endpoint returns 9 held-out rows, each with 460 test contexts.
- Rainfall artifact metric is honestly reported as `CSI@50mm`; the active artifact does not provide CSI@20mm.
- Confidence decay is normalized from real per-lead trust scores: 0.401, 0.377, 0.353, 0.329, 0.305 for 24h through 120h.
- Null remains unavailable; measured zero remains zero.

## Validation evidence

- New integrity tests: 7 passed.
- Backend suite plus integrity tests: 27 passed, 2 skipped.
- Frontend production build: passed.
- Final live status: GFS VALID/LIVE, IFS VALID/LIVE, AIFS VALID/LIVE.

The corrected +72h KWG result is the key integrity proof: AIFS is 6.60 mm/24h, not a multi-thousand-mm value; raw blend is 5.23 and final is 4.15 after applying the existing calibration only to semantically valid inputs.
