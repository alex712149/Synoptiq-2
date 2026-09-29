import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))

import live_refresh


def test_provider_fallback_is_used_after_primary_failure(monkeypatch):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    calls = []
    monkeypatch.setattr(live_refresh.time, "sleep", lambda _: None)

    def primary(model, retrieved_at):
        calls.append("primary")
        raise RuntimeError("primary unavailable")

    def fallback(model, retrieved_at):
        calls.append("fallback")
        rows = []
        for zone in live_refresh.ZONES:
            for lead in live_refresh.LEADS:
                for variable, value in (("temperature", 25.0), ("precipitation", 1.0), ("wind_speed", 12.0)):
                    rows.append({
                        "model": model, "region": zone, "variable": variable,
                        "lead_hours": lead, "valid_time": (now + __import__("datetime").timedelta(hours=lead)).replace(tzinfo=None),
                        "forecast_value": value,
                        "source_provider": "fallback", "source_model": "fallback", "source_transport": "https",
                    })
        return rows

    monkeypatch.setattr(live_refresh, "_live_rows", primary)
    monkeypatch.setattr(live_refresh, "_fallback_rows", fallback)
    rows, state = live_refresh.fetch_provider("GFS", now)
    assert len(rows) == 45
    assert state["status"] == "LIVE"
    assert state["fallback_used"] is True
    assert calls[-1] == "fallback"
    assert calls[:-1] == ["primary"] * 5


def test_aifs_fallback_uses_latest_published_cycle_and_source_timestamps(monkeypatch):
    now = datetime(2026, 9, 29, 16, 0, tzinfo=timezone.utc)
    requested = []

    def fetch_cycle(model, run_date, hour, steps, maximum_retries=4):
        requested.append((run_date, hour))
        if hour == 12:
            return []
        return [
            {
                "run_date": run_date,
                "run_hour": hour,
                "model_generation": "AIFS Single v2",
                "step": step,
                "zone": zone,
                "t2m_c": 25.0,
                "wind_ms": 3.0,
                "tp_cum_m": step / 1000,
            }
            for zone in live_refresh.ZONES
            for step in steps
        ]

    monkeypatch.setitem(sys.modules, "fetch_ecmwf", SimpleNamespace(fetch_cycle=fetch_cycle))
    rows = live_refresh._fallback_rows("AIFS", now)

    assert requested == [("2026-09-29", 12), ("2026-09-29", 0)]
    assert len(rows) == 45
    assert rows[0]["run_time"] == datetime(2026, 9, 29, 0)
    assert rows[0]["valid_time"] == now.replace(tzinfo=None) + timedelta(hours=24)
    assert rows[0]["source_run_time"] == "2026-09-29T00:00:00+00:00"
    assert rows[0]["run_time_basis"] == "model_run_time"
    assert rows[0]["model_generation"] == "live:AIFS Single v2"
    assert rows[0]["source_model"] == "AIFS Single"
    assert rows[0]["source_transport"] == "ECMWF Open Data"
    assert rows[0]["valid_time"] > now.replace(tzinfo=None)


def test_aifs_ecmwf_503_uses_exponential_backoff(monkeypatch):
    now = datetime(2026, 9, 29, 16, 0, tzinfo=timezone.utc)
    requested = []
    delays = []

    def fetch_cycle(model, run_date, hour, steps, maximum_retries=4):
        requested.append((run_date, hour))
        if len(requested) <= 4:
            raise RuntimeError("HTTP 503 Slow Down")
        return [
            {
                "run_date": run_date,
                "run_hour": hour,
                "model_generation": "AIFS Single v2",
                "step": step,
                "zone": zone,
                "t2m_c": 25.0,
                "wind_ms": 3.0,
                "tp_cum_m": step / 1000,
            }
            for zone in live_refresh.ZONES
            for step in steps
        ]

    monkeypatch.setitem(sys.modules, "fetch_ecmwf", SimpleNamespace(fetch_cycle=fetch_cycle))
    monkeypatch.setattr(live_refresh.time, "sleep", delays.append)
    rows = live_refresh._fallback_rows("AIFS", now)

    assert requested == [("2026-09-29", 12)] * 5
    assert delays == [5, 10, 20, 30]
    assert len(rows) == 45
    assert rows[0]["source_run_time"] == "2026-09-29T12:00:00+00:00"
