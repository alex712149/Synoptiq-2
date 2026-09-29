from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))
import live_refresh


def test_aifs_identity_and_native_semantics_are_preserved():
    assert live_refresh.MODELS["AIFS"] == ("aifs-single", "ECMWF AIFS 0.25 Single")
    row = {
        "model": "AIFS", "region": live_refresh.ZONES[0], "variable": "precipitation",
        "lead_hours": 24, "valid_time": datetime(2026, 9, 30),
        "forecast_value": 12.0, "tp_native_unit": "kg m**-2", "tp_step_type": "accum",
    }
    rows = []
    for zone in live_refresh.ZONES:
        for lead in live_refresh.LEADS:
            for variable, value in (("temperature", 25.0), ("precipitation", 12.0), ("wind_speed", 12.0)):
                rows.append({**row, "region": zone, "variable": variable, "lead_hours": lead,
                             "valid_time": datetime(2026, 9, 29, tzinfo=timezone.utc).replace(tzinfo=None) + __import__("datetime").timedelta(hours=lead),
                             "forecast_value": value})
    coverage = live_refresh.validate_rows("AIFS", rows, datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert coverage["semantic_valid"] is True


def test_multi_thousand_precipitation_is_rejected_before_blend():
    rows = []
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    for zone in live_refresh.ZONES:
        for lead in live_refresh.LEADS:
            for variable, value in (("temperature", 25.0), ("precipitation", 6597.7), ("wind_speed", 12.0)):
                rows.append({"model": "AIFS", "region": zone, "variable": variable,
                             "lead_hours": lead, "valid_time": now.replace(tzinfo=None) + __import__("datetime").timedelta(hours=lead),
                             "forecast_value": value, "tp_native_unit": "kg m**-2", "tp_step_type": "accum"})
    try:
        live_refresh.validate_rows("AIFS", rows, now)
    except RuntimeError as exc:
        assert "physical semantic range" in str(exc)
    else:
        raise AssertionError("multi-thousand precipitation was accepted")
