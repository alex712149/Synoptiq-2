from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))
import live_refresh


def test_invalid_semantics_do_not_produce_live_provider_state(monkeypatch):
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    invalid = []
    for zone in live_refresh.ZONES:
        for lead in live_refresh.LEADS:
            for variable, value in (("temperature", 25.0), ("precipitation", 5000.0), ("wind_speed", 12.0)):
                invalid.append({
                    "model": "AIFS", "region": zone, "variable": variable,
                    "lead_hours": lead, "valid_time": (now + __import__("datetime").timedelta(hours=lead)).replace(tzinfo=None),
                    "forecast_value": value, "tp_native_unit": "kg m**-2", "tp_step_type": "accum",
                })

    monkeypatch.setattr(live_refresh, "_live_rows", lambda model, retrieved_at: invalid)
    monkeypatch.setattr(live_refresh, "_fallback_rows", lambda model, retrieved_at: invalid)
    rows, state = live_refresh.fetch_provider("AIFS", now)
    assert rows == []
    assert state["status"] == "INVALID"
    assert state["semantic_valid"] is False
