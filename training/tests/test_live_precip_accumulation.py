from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "realdata"))
import live_refresh


def _raw_cycle():
    rows = []
    for zone in live_refresh.ZONES:
        for step in range(6, 175, 6):
            rows.append({
                "run_date": "2026-09-29", "run_hour": 0, "step": step,
                "zone": zone, "model_generation": "AIFS Single v2",
                "t2m_c": 25.0, "wind_ms": 3.0,
                "tp_cum_m": step * 0.1,
                "tp_native_unit": "kg m**-2", "tp_step_type": "accum",
            })
    return rows


def test_cumulative_ecmwf_precipitation_uses_difference_without_thousand_multiplier():
    retrieved = datetime(2026, 9, 29, 0, tzinfo=timezone.utc)
    rows = live_refresh._aggregate_archive_rows(
        "AIFS", _raw_cycle(), retrieved, "ECMWF Open Data", "ECMWF Open Data"
    )
    precipitation = [
        row["forecast_value"]
        for row in rows
        if row["region"] == "kerala_western_ghats"
        and row["variable"] == "precipitation"
        and row["lead_hours"] == 24
    ][0]
    assert precipitation == pytest.approx(2.4)
    assert rows[0]["tp_native_unit"] == "kg m**-2"
    assert rows[0]["precip_accumulation"] == "cumulative_difference_24h"
