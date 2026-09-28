# Deployment

Synoptiq has three separately deployed concerns: the Vercel frontend, the Render FastAPI web service, and a separate Render Cron Job for latest-cycle ingestion. PostgreSQL is the production source of truth. The Render filesystem is not used for permanent raw data.

## Render

Use `render.yaml` or create the web service and cron job separately. Set `SYNOPTIQ_MODE=real`, `DATABASE_URL`, `SYNOPTIQ_MODEL_VERSION`, `SYNOPTIQ_CORS_ORIGINS`, `NASA_EARTHDATA_USERNAME`, and `NASA_EARTHDATA_PASSWORD` in Render secrets. ERA5 uses the public Open-Meteo Historical Weather API. Package the selected model under `models/real/`, its manifest under `artifacts/real/manifests/<SYNOPTIQ_MODEL_VERSION>/`, and calibration under `artifacts/real/calibration/`; the Cron Job filesystem is not shared with the Web Service. The API reports `ready: false` until its real manifest, models, calibration, database, live blend, and all three source runs exist.

Historical training uses `TRAINING_DATABASE_URL` locally and never receives or changes the production `DATABASE_URL`. It writes a new immutable manifest and prototype/metrics version; promote those with the selected real models and calibration before scheduling ingestion.

## Vercel

Set only `VITE_API_BASE_URL` to the Render `/api/v1` URL and leave `VITE_APP_MODE=LIVE`. Do not add NOAA, ECMWF, NASA, CDS, PostgreSQL, or model credentials to Vercel.

## Local

Use the existing `D:\SIH2026\.venv`. Set `SYNOPTIQ_MODE=real` to use the real prototype or `SYNOPTIQ_MODE=fake` to use the explicit local demo archive. Real mode requires PostgreSQL for normal serving; local validation can select `SYNOPTIQ_DATABASE_ROLE=TRAINING` with `TRAINING_DATABASE_URL` pointing to `data/real/training.sqlite3`.
