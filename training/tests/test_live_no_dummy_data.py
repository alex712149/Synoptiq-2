from pathlib import Path


def test_real_live_refresh_has_no_dummy_provider_labels():
    source = Path(__file__).parents[1] / "realdata" / "live_refresh.py"
    text = source.read_text(encoding="utf-8").lower()
    forbidden = ("fallback_value", "fallback_forecast", "synthetic aifs", "dummy forecast")
    assert not any(token in text for token in forbidden)
