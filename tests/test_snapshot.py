import pandas as pd

from snapshot import summarize


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "NIFTY",
                "type": "CE",
                "strike": 100,
                "oi": 10,
                "iv": 0.2,
                "gamma": 0.01,
                "gex": 50,
                "underlying": 100,
                "expiry": "21-Aug-2026",
                "ingestion_timestamp": pd.Timestamp("2026-08-21 10:00:00"),
            },
            {
                "symbol": "NIFTY",
                "type": "PE",
                "strike": 100,
                "oi": 20,
                "iv": 0.22,
                "gamma": 0.01,
                "gex": -40,
                "underlying": 100,
                "expiry": "21-Aug-2026",
                "ingestion_timestamp": pd.Timestamp("2026-08-21 10:00:00"),
            },
        ]
    )


def test_summarize_levels():
    s = summarize(_frame())
    assert s["spot"] == 100.0
    assert s["n_rows"] == 2
    assert s["pcr"] == 2.0
    assert s["net_gex"] == 10.0
    assert s["total_oi"] == 30
    assert "LONG" in s["regime"] or "SHORT" in s["regime"] or s["regime"] == "NEUTRAL Γ"


def test_summarize_empty():
    assert summarize(pd.DataFrame()) == {}
