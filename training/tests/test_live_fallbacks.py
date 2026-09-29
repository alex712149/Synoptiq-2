import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))

import live_refresh


def test_provider_fallback_is_used_after_primary_failure(monkeypatch):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    calls = []

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
