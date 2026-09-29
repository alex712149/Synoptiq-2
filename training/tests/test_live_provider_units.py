from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))
import live_refresh


def _rows(value=10.0, unit="kg m**-2", step_type="accum"):
    rows = []
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    for zone in live_refresh.ZONES:
        for lead in live_refresh.LEADS:
            for variable, forecast in (("temperature", 25.0), ("precipitation", value), ("wind_speed", 12.0)):
                rows.append({
                    "model": "AIFS", "region": zone, "variable": variable,
                    "lead_hours": lead, "valid_time": (now + __import__("datetime").timedelta(hours=lead)).replace(tzinfo=None),
                    "forecast_value": forecast, "tp_native_unit": unit, "tp_step_type": step_type,
                })
    return rows


def test_ecmwf_native_precipitation_unit_is_semantically_accepted():
    coverage = live_refresh.validate_rows("AIFS", _rows(), datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert coverage["semantic_valid"] is True
    assert coverage["semantic_reason"]


def test_wrong_ecmwf_native_unit_is_rejected():
    try:
        live_refresh.validate_rows("AIFS", _rows(unit="m"), datetime(2026, 9, 29, tzinfo=timezone.utc))
    except RuntimeError as exc:
        assert "native unit" in str(exc)
    else:
        raise AssertionError("wrong ECMWF precipitation unit was accepted")
