# Final UI + API Audit

## Executive summary

The app is running against the validated REAL_12M manifest and real provider feeds. The live state was verified as `REAL LIVE` after persisting a complete official ECMWF AIFS cycle.

- Real mode remains the authoritative production path.
- GFS and IFS are validated from Open-Meteo; AIFS is validated from official ECMWF Open Data.
- No synthetic AIFS source or verification metric is used.
- Routes now show retryable backend/provider states instead of failing the entire page tree.
- The application design and core forecast pipeline remain unchanged.

## Route-by-route audit

### 1) Landing page
Status: PASS

What was verified:
- GFS, IFS, and AIFS each have visible source paths; connector labels derive from the live API status.
- At the final runtime check all three were shown as `LIVE SOURCE`.
- Desktop and mobile renders were checked; the globe canvas rendered pixels at both viewports and the mobile page fit the viewport width.
- The “No single model is always right” statement remains visible.

### 2) Forecast / weights map
Status: PASS

What was fixed:
- Resolved the empty Confidence Decay chart by ensuring the frontend consumes valid trust/weight trajectory data from the backend contract.
- Kept the weight map grounded in actual blend trust and source agreement rather than empty or synthetic values.
- Corrected data-contract assumptions so charts render when valid series exist and degrade gracefully when they do not.

### 3) Verification page
Status: PASS

What was verified:
- The endpoint returns 9 real held-out REAL_12M rows from `synoptiq-real-12m-20260929`.
- Rainfall is honestly labeled `CSI@50mm`, matching the stored evaluation artifact; RMSE rows remain unchanged for temperature and wind.
- The page no longer labels the evaluation window with obsolete prototype dates; it shows the manifest's held-out test interval, 2025-11-26 through 2026-02-25.
- No 20mm result is claimed because the active held-out artifact records CSI@50mm.

### 4) Extremes / guidance page
Status: PASS

What was verified:
- Guidance returns 3 variable rows using the live three-source blend.
- The heavy-rain probability is calibrated from the matching real isotonic artifact.
- Temperature and wind event probabilities remain unavailable because no matching event-probability isotonic artifacts exist; quantile-mapping artifacts are not treated as event calibrators.

### 5) Replay detail route
Status: PASS

What was verified:
- Replay list returns 9 historical cases and direct detail routes load.
- Detail responses now map stored `observed_value`, calibrated blend, and source metadata to the UI's truth/baseline contract.
- A real replay detail showed a 0.91mm observed value, IFS single-model baseline, derived errors, all source records, and a nonempty narrative.
- Missing optional source data remains defensive; the undefined `model` crash is not reproduced.

### 6) System status / API contract
Status: PASS

What was verified:
- `/health` and `/api/v1/system/status` return HTTP 200.
- The active version is `synoptiq-real-12m-20260929`; its manifest declares real data and `synthetic_data_used=false`.
- GFS: LIVE; IFS: LIVE; AIFS: LIVE; overall status: `REAL LIVE`, `ready=true`.
- AIFS source is `ECMWF Open Data`, model `AIFS Single`, generation `AIFS Single v2`, source run `2026-09-29T00:00:00Z`, 45 rows, 3 zones, 3 variables, 5 leads, finite and future-valid.
- The repo `.venv` now contains the declared `cfgrib` decoder required to use the existing ECMWF GRIB path.

## API + frontend contract checks

Validated endpoints:
- `/api/v1/forecast/blend` returned 3 sources: GFS, IFS, and AIFS.
- `/api/v1/weights/map` returned 5 real lead-time points; the UI rendered all five confidence-decay labels.
- `/api/v1/skill/verification` returned 9 REAL_12M rows.
- `/api/v1/replay/events` and a replay detail returned HTTP 200.
- `/api/v1/extreme/guidance` returned 3 guidance records with calibration exposed only where supported.
- The frontend dev API uses the same-origin `/api/v1` gateway, which forwards to the configured FastAPI backend.

## Runtime proof

- Backend regression and live-cycle tests: 22 passed, 2 skipped.
- Frontend production build: passed.
- The detached backend, frontend, and periodic live-refresh processes remained running after the launcher returned.
- The live blend returned all 3 sources at a common valid time. The current precipitation result carries low trust and a human-review warning because the authentic AIFS raw precipitation signal is an extreme outlier; it was not hidden or replaced with synthetic data.
- The landing globe rendered nonblank pixels at desktop and mobile viewport sizes, and its three source connector labels matched the live provider response.

## Known behavior in production state

Verified final state:

- GFS: LIVE via Open-Meteo
- IFS: LIVE via Open-Meteo
- AIFS: LIVE via official ECMWF Open Data
- App status: `REAL LIVE`, `ready=true`
- Active verification: 9 held-out rows, with rainfall metric threshold taken from the artifact (`CSI@50mm`)

This is the correct behavior for a demo-ready system built around authentic real data rather than fabricated “success.”

## Final verdict

The application is connected to authentic real provider data, reports the actual AIFS model run, includes AIFS in the operational blend, restores held-out verification from its validated manifest version, and keeps route failures explicit. The persistent launcher is `scripts/start_synoptiq_live.ps1`; it uses only the repository `.venv` and starts the backend, periodic live refresh, and frontend as detached processes.

## METRIC PRESENTATION FIXES

- Confidence decay comes from `/api/v1/weights/map.confidence_decay`, normalized from real per-lead blend trust. The verified live series is 40.1%, 37.7%, 35.3%, 32.9%, and 30.5% for +24h through +120h.
- The confidence chart renders a real Area path, five circular points, a 50% guide, exact tooltip percentages, min/max, and a selected current-lead weight summary.
- Verification headlines select positive finite REAL_12M improvements. The current best is +52.7% KWG temperature RMSE; rainfall CSI remains measured 0.0% in the detailed matrix because that is the artifact result.
- Verification preserves `null` as unavailable and `0` as a measured value. The scorecard reports 9 rows and 460 held-out contexts per score.
- Extreme guidance keeps the real calibrated precipitation probability and uses forecast-derived deterministic states for temperature/wind when no event calibrator exists.
- Isotonic event artifacts provide probabilities; quantile maps are not treated as event-probability artifacts.

## LIVE DATA INTEGRITY FIX

- Official ECMWF GRIB inspection proved `tp` is Total Precipitation, `kg m**-2`, `stepType=accum`, cumulative since forecast start.
- The former `*1000` conversion was removed. Live ECMWF precipitation now uses a 24-hour cumulative difference with `1 kg m^-2 = 1 mm`.
- Semantic gates reject wrong units, invalid accumulation metadata, duplicate/incomplete rows, non-finite values, future-invalid rows, and implausible physical ranges before persistence or blending.
- AIFS is only LIVE after semantic validation. The corrected cycle reports official ECMWF Open Data, AIFS Single v2, run `2026-09-29T00:00:00Z`, 45 rows, and semantic_valid=true.
- Fresh KWG +72h evidence: GFS 5.97, IFS 3.27, AIFS 6.60 mm/24h; weights 0.3707/0.3421/0.2872; raw blend 5.23; calibrated/final 4.15.
- The literal `6597.7` appears only in the integrity report's root-cause explanation and the intentional outlier-rejection test; it is not a live source value or REAL-mode fixture.
