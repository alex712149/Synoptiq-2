"""Independent real-time provider refresh for GFS, IFS, and AIFS."""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIVE_DIR = Path(os.getenv("SYNOPTIQ_LIVE_DATA_DIR", str(ROOT / "data" / "real" / "live"))).resolve()
LOG_PATH = LIVE_DIR / "live_refresh.log"
MODEL_VERSION = os.getenv("SYNOPTIQ_MODEL_VERSION", "synoptiq-real-12m-20260929")
LEADS = [24, 48, 72, 96, 120]
ZONES = ["kerala_western_ghats", "bay_of_bengal_east_coast", "indo_gangetic_plains"]
MODELS = {
    "GFS": ("gfs", "NCEP GFS Global 0.11/0.25"),
    "IFS": ("ifs", "ECMWF IFS 0.25"),
    "AIFS": ("aifs-single", "ECMWF AIFS 0.25 Single"),
}

LIVE_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(message)s")


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def _live_rows(model: str, retrieved_at: datetime) -> list[dict]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_openmeteo import REPRESENTATIVE_POINTS, fetch_live_cycle

    source_model = MODELS[model][1]
    source_rows = fetch_live_cycle(MODELS[model][0], retrieved_at.strftime("%Y-%m-%d"))
    rows = []
    for item in source_rows:
        lead = int(item["step"])
        valid_time = retrieved_at + timedelta(hours=lead)
        common = {
            "model": model,
            "region": item["zone"],
            "valid_time": valid_time.replace(tzinfo=None),
            "lead_hours": lead,
            "run_time": retrieved_at.replace(tzinfo=None),
            "model_generation": f"live:{source_model}",
            "season": _season(valid_time.month),
            "regime": "normal",
            "regime_probs": None,
            "lat": float(np.mean([point[0] for point in REPRESENTATIVE_POINTS[item["zone"]]])),
            "lon": float(np.mean([point[1] for point in REPRESENTATIVE_POINTS[item["zone"]]])),
            "retrieved_at_utc": retrieved_at.isoformat(),
            "source_provider": "Open-Meteo",
            "source_model": source_model,
            "source_transport": "https",
            "source_run_time": None,
            "run_time_basis": "retrieval_time",
        }
        rows.extend([
            {**common, "variable": "temperature", "forecast_value": float(item["t2m_c"])},
            {**common, "variable": "precipitation", "forecast_value": float(item["precip_mm"])},
            {**common, "variable": "wind_speed", "forecast_value": float(item["wind_ms"]) * 3.6},
        ])
    return rows


def _fallback_rows(model: str, retrieved_at: datetime) -> list[dict]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if model == "GFS":
        import fetch_gfs
        raw = fetch_gfs.fetch_cycle(retrieved_at.strftime("%Y-%m-%d"), (retrieved_at.hour // 6) * 6, list(range(6, 145, 6)))
        return _aggregate_archive_rows(model, raw, retrieved_at, "NOAA/AWS", "noaa-gfs-bdp-pds")
    import fetch_ecmwf
    source_name = "ECMWF Open Data AWS"
    raw = fetch_ecmwf.fetch_cycle(MODELS[model][0], retrieved_at.strftime("%Y-%m-%d"), (retrieved_at.hour // 6) * 6, list(range(6, 145, 6)))
    return _aggregate_archive_rows(model, raw, retrieved_at, source_name, "ecmwf-forecasts-s3")


def _aggregate_archive_rows(model: str, raw_rows: list[dict], retrieved_at: datetime, provider: str, transport: str) -> list[dict]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_openmeteo import REPRESENTATIVE_POINTS
    frame = pd.DataFrame(raw_rows)
    if frame.empty:
        raise RuntimeError("fallback returned no rows")
    rows = []
    for zone, group in frame.groupby("zone"):
        indexed = group.set_index("step")
        for lead in LEADS:
            steps = [lead + offset for offset in (0, 6, 12, 18)]
            if any(step not in indexed.index for step in steps):
                raise RuntimeError(f"fallback missing {zone} lead {lead}")
            subset = indexed.loc[steps]
            if model == "GFS":
                precip_steps = [lead + offset for offset in (6, 12, 18, 24)]
                if any(step not in indexed.index for step in precip_steps):
                    raise RuntimeError(f"fallback missing {zone} precipitation lead {lead}")
                precipitation = float(indexed.loc[precip_steps, "apcp6_mm"].clip(lower=0).sum())
            else:
                if lead + 24 not in indexed.index:
                    raise RuntimeError(f"fallback missing {zone} cumulative precipitation lead {lead}")
                precipitation = max(0.0, float(indexed.loc[lead + 24, "tp_cum_m"] - indexed.loc[lead, "tp_cum_m"]) * 1000.0)
            valid_time = retrieved_at + timedelta(hours=lead)
            common = {
                "model": model, "region": zone, "valid_time": valid_time.replace(tzinfo=None),
                "lead_hours": lead, "run_time": retrieved_at.replace(tzinfo=None),
                "model_generation": f"live:{MODELS[model][1]}", "season": _season(valid_time.month),
                "regime": "normal", "regime_probs": None,
                "lat": float(np.mean([point[0] for point in REPRESENTATIVE_POINTS[zone]])),
                "lon": float(np.mean([point[1] for point in REPRESENTATIVE_POINTS[zone]])),
                "retrieved_at_utc": retrieved_at.isoformat(), "source_provider": provider,
                "source_model": MODELS[model][1], "source_transport": transport,
                "source_run_time": None, "run_time_basis": "retrieval_time",
            }
            rows.extend([
                {**common, "variable": "temperature", "forecast_value": float(subset["t2m_c"].mean())},
                {**common, "variable": "precipitation", "forecast_value": precipitation},
                {**common, "variable": "wind_speed", "forecast_value": float(subset["wind_ms"].max()) * 3.6},
            ])
    return rows


def _season(month: int) -> str:
    if month in (3, 4, 5):
        return "pre_monsoon"
    if month in (6, 7, 8, 9):
        return "sw_monsoon"
    if month in (10, 11):
        return "post_monsoon"
    return "winter"


def validate_rows(model: str, rows: list[dict], now: datetime) -> dict:
    frame = pd.DataFrame(rows)
    expected = {(zone, variable, lead) for zone in ZONES for variable in ("temperature", "precipitation", "wind_speed") for lead in LEADS}
    observed = set(zip(frame["region"], frame["variable"], frame["lead_hours"])) if not frame.empty else set()
    finite = bool(not frame.empty and np.isfinite(frame["forecast_value"].to_numpy(dtype=float)).all())
    future = bool(not frame.empty and (pd.to_datetime(frame["valid_time"]) > now.replace(tzinfo=None)).all())
    complete = observed == expected and len(frame) == len(expected)
    duplicate = int(frame.duplicated(["model", "region", "variable", "lead_hours", "valid_time"]).sum()) if not frame.empty else 0
    if not complete or not finite or not future or duplicate:
        raise RuntimeError(f"{model} invalid live cycle: complete={complete} finite={finite} future={future} duplicates={duplicate}")
    return {"rows": len(frame), "regions": len(set(frame["region"])), "variables": len(set(frame["variable"])), "leads": len(set(frame["lead_hours"])), "finite": finite, "complete": complete, "future": future}


def fetch_provider(model: str, now: datetime) -> tuple[list[dict], dict]:
    started = time.monotonic()
    fallback_used = False
    error = None
    for attempt, delay in enumerate((0, 2, 5, 10, 20)):
        if delay:
            time.sleep(delay)
        try:
            rows = _live_rows(model, now)
            coverage = validate_rows(model, rows, now)
            source_provider = rows[0]["source_provider"]
            state = {"status": "LIVE", "fresh": True, "complete": True, "finite": True, "source": source_provider, "source_model": rows[0]["source_model"], "source_transport": rows[0]["source_transport"], "retrieved_at": now.isoformat(), "source_run_time": None, "run_time_basis": "retrieval_time", "coverage": coverage, "fallback_used": fallback_used, "reason": "complete future real forecast cycle", "latency_seconds": round(time.monotonic() - started, 3)}
            return rows, state
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logging.warning("provider=%s attempt=primary-%s failure=%s", model, attempt + 1, error)
    try:
        rows = _fallback_rows(model, now)
        coverage = validate_rows(model, rows, now)
        state = {"status": "LIVE", "fresh": True, "complete": True, "finite": True, "source": rows[0]["source_provider"], "source_model": rows[0]["source_model"], "source_transport": rows[0]["source_transport"], "retrieved_at": now.isoformat(), "source_run_time": None, "run_time_basis": "retrieval_time", "coverage": coverage, "fallback_used": True, "reason": "complete future real fallback cycle", "latency_seconds": round(time.monotonic() - started, 3)}
        return rows, state
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logging.warning("provider=%s attempt=fallback failure=%s", model, error)
    state = {"status": "UNAVAILABLE", "fresh": False, "complete": False, "finite": False, "source": None, "source_model": None, "source_transport": None, "retrieved_at": now.isoformat(), "source_run_time": None, "run_time_basis": "retrieval_time", "coverage": {}, "fallback_used": True, "reason": error or "provider failed", "latency_seconds": round(time.monotonic() - started, 3)}
    return [], state


def persist_cycle(provider_rows: dict[str, list[dict]], states: dict[str, dict], now: datetime) -> None:
    from app.config import LIVE_DATA_DIR
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.models_db import ForecastRow, LiveForecast
    from app.config import ACTIVE_MODEL_VERSION
    for model, rows in provider_rows.items():
        if rows:
            _atomic_write_parquet(pd.DataFrame(rows), LIVE_DIR / f"{model.lower()}_latest.parquet")
    manifest = {"last_refresh": now.isoformat(), "model_version": ACTIVE_MODEL_VERSION or MODEL_VERSION, "providers": states, "blend_readiness": sum(state["status"] == "LIVE" for state in states.values()) >= 2, "frontend_readiness": True}
    temporary = LIVE_DIR / "live_manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary.replace(LIVE_DIR / "live_manifest.json")
    if sum(bool(rows) for rows in provider_rows.values()) < 2:
        return
    db = SessionLocal()
    db.query(ForecastRow).filter(ForecastRow.model_generation.like("live:%")).delete(synchronize_session=False)
    db.query(LiveForecast).delete(synchronize_session=False)
    for rows in provider_rows.values():
        for row in rows:
            db.add(ForecastRow(model=row["model"], model_generation=row["model_generation"], region=row["region"], run_time=row["run_time"], valid_time=row["valid_time"], lead_hours=row["lead_hours"], variable=row["variable"], lat=row["lat"], lon=row["lon"], forecast_value=row["forecast_value"], season=row["season"], regime=row["regime"], regime_probs=row["regime_probs"]))
    db.add(LiveForecast(region="__cycle__", variable="__cycle__", valid_time=now.replace(tzinfo=None), lead_hours=0, run_time=now.replace(tzinfo=None), ingestion_time=now.replace(tzinfo=None), model_version=ACTIVE_MODEL_VERSION or MODEL_VERSION, source_runs=states, payload=manifest))
    db.commit()
    db.close()


def refresh_once() -> dict:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    provider_rows, states = {}, {}
    for model in MODELS:
        rows, state = fetch_provider(model, now)
        provider_rows[model] = rows
        states[model] = state
        logging.info("provider=%s source=%s success=%s fallback=%s rows=%s valid_min=%s valid_max=%s freshness=%s", model, state.get("source"), state["status"] == "LIVE", state["fallback_used"], state.get("coverage", {}).get("rows", 0), rows[0]["valid_time"].isoformat() if rows else None, rows[-1]["valid_time"].isoformat() if rows else None, state["fresh"])
    persist_cycle(provider_rows, states, now)
    return states


def main() -> None:
    interval = int(os.getenv("SYNOPTIQ_LIVE_REFRESH_MINUTES", "15"))
    once = "--once" in sys.argv
    while True:
        try:
            states = refresh_once()
            print(json.dumps(states, indent=2), flush=True)
        except Exception as exc:
            logging.exception("refresh cycle failed: %s", exc)
            print(f"live refresh cycle failed: {exc}", flush=True)
        if once:
            return
        time.sleep(max(60, interval * 60))


if __name__ == "__main__":
    main()
