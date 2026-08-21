from export_diff import diff_to_csv
import pandas as pd


def test_diff_csv_contains_keys():
    csv_text = diff_to_csv({"d_spot": 2.0, "regime_changed": True})
    assert "d_spot" in csv_text
    assert "2.0" in csv_text


def test_diff_csv_appends_movers():
    movers = pd.DataFrame([{"strike": 100, "d_oi": 30}])
    csv_text = diff_to_csv({"d_spot": 1}, movers)
    assert "strike" in csv_text
    assert "30" in csv_text
